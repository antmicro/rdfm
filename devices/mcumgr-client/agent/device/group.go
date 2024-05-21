package device

import (
	"fmt"
	"log/slog"
	"path"
	"slices"
	"time"

	"rdfm-mcumgr-client/appcfg"
	"rdfm-mcumgr-client/mcumgr"
	"rdfm-mcumgr-client/rdfm/api"
	"rdfm-mcumgr-client/rdfm/artifact"
)

type (
	Group struct {
		Cfg      appcfg.GroupConfig
		Log      *slog.Logger
		GroupKey *DeviceKey

		currVersion string

		members []member
	}

	member struct {
		target string
		dev    *mcumgr.Device
	}
)

func InitGroup(gCfg appcfg.GroupConfig, cfg *appcfg.AppConfig, log *slog.Logger) (*Group, error) {
	key, err := InitDeviceKey(path.Join(cfg.KeyDir, gCfg.Key), log)
	if err != nil {
		return nil, err
	}

	members := make([]member, 0, len(gCfg.Members))
	var currVersion string
	for i, m := range gCfg.Members {
		mLog := log.With(slog.String("member", m.Name))

		dev, err := mcumgr.InitDevice(m.Transport, mLog)
		if err != nil {
			return nil, err
		}

		if i == 0 {
			currVersion = dev.PrimaryImage.Version
		} else if devVersion := dev.PrimaryImage.Version; currVersion != devVersion {
			return nil, fmt.Errorf(
				"Version mismatch between group members (%s: '%s', %s: '%s')",
				gCfg.Members[0].Name,
				currVersion,
				m.Name,
				devVersion,
			)
		}

		members = append(members, member{
			target: m.Device,
			dev:    dev,
		})
	}

	if len(members) == 0 {
		return nil, fmt.Errorf("Group has no members")
	}

	return &Group{
		Cfg:         gCfg,
		Log:         log,
		GroupKey:    key,
		currVersion: currVersion,
		members:     members,
	}, nil
}

// All members are running same version
func (g *Group) Version() string {
	return g.currVersion
}

func (g *Group) Metadata() api.DeviceMetadata {
	return api.DeviceMetadata{
		DeviceType:      g.Cfg.Type,
		SoftwareVersion: g.Version(),
		MacAddress:      g.Cfg.Id,
	}
}

func (g *Group) Members() int {
	return len(g.members)
}

func (g *Group) Key() *DeviceKey {
	return g.GroupKey
}

func (g *Group) Logger() *slog.Logger {
	return g.Log
}

func (g *Group) RunUpdate(a artifact.Artifact) error {
	log := g.Log

	art, ok := a.(*artifact.GroupArtifact)
	if !ok {
		return fmt.Errorf("Unsupported artifact type (%T)", art)
	}

	// First check if the artifact contains updates for all group members
	for _, m := range g.members {
		if _, ok := art.Images[m.target]; !ok {
			return fmt.Errorf("Artifact doesn't contain an image for member '%s'", m.target)
		}
	}

	currImgHashes := make([][]byte, 0, len(g.members))
	for _, m := range g.members {
		currImgHashes = append(currImgHashes, m.dev.PrimaryImage.Hash)
	}

	waitAll := func(errC <-chan error) error {
		var err error
		for num := len(g.members); num > 0; num-- {
			if e := <-errC; e != nil {
				err = e
			}
		}
		return err
	}
	errC := make(chan error)

	log.Info("Starting update")
	for _, m := range g.members {
		go writeImage(art.Images[m.target].Data, m.dev, errC)
	}
	if err := waitAll(errC); err != nil {
		return err
	}

	log.Debug("Setting images to pending")
	for _, m := range g.members {
		go setPending(m.dev, errC)
	}
	if err := waitAll(errC); err != nil {
		return err
	}

	log.Info("Rebooting")
	for _, m := range g.members {
		go reboot(m.dev, errC)
	}
	if err := waitAll(errC); err != nil {
		return err
	}

	log.Debug("Checking update")
	for _, m := range g.members {
		go checkUpdate(m.dev, errC)
	}
	if err := waitAll(errC); err != nil {
		// At least one update was rejected - reboot all devices in group without confirming image
		for _, m := range g.members {
			go reboot(m.dev, errC)
		}

		return err
	}

	log.Debug("Confirming update")
	for _, m := range g.members {
		go confirmImage(m.dev, errC)
	}
	if err := waitAll(errC); err != nil {
		log.Error("Update failed. Attempting rollback")

		for i, m := range g.members {
			go rollback(currImgHashes[i], m.dev, errC)
		}
		if e := waitAll(errC); e != nil {
			log.Error("Rollback failed")
			return err
		}

		log.Info("Rollback finished", slog.String("restored_version", g.currVersion))
		return err
	}

	g.currVersion = g.members[0].dev.PrimaryImage.Version

	return nil
}

func writeImage(image []byte, dev *mcumgr.Device, errC chan<- error) {
	session, err := dev.Transport.AcqSession()
	if err != nil {
		errC <- err
		return
	}
	defer session.Close()

	if err := session.WriteImage(image); err != nil {
		errC <- err
		return
	}

	primary, secondary, err := readImages(session)
	if err != nil {
		errC <- err
		return
	}

	if slices.Compare(primary.Hash, secondary.Hash) == 0 {
		errC <- fmt.Errorf("Can't update using currently running version")
		return
	}

	errC <- nil
}

func setPending(dev *mcumgr.Device, errC chan<- error) {
	session, err := dev.Transport.AcqSession()
	if err != nil {
		errC <- err
		return
	}
	defer session.Close()

	_, secondary, err := readImages(session)
	if err != nil {
		errC <- err
		return
	}
	if err := session.SetPendingImage(secondary.Hash); err != nil {
		errC <- err
		return
	}

	errC <- nil
}

func reboot(dev *mcumgr.Device, errC chan<- error) {
	session, err := dev.Transport.AcqSession()
	if err != nil {
		errC <- err
		return
	}
	defer session.Close()

	if err := session.ResetDevice(); err != nil {
		errC <- err
		return
	}

	time.Sleep(rebootCheckInterval)

	errC <- nil
}

func checkUpdate(dev *mcumgr.Device, errC chan<- error) {
	mLog := dev.Log

	session, err := dev.Transport.AcqSession()
	if err != nil {
		errC <- err
		return
	}
	defer session.Close()

	passed := time.Duration(0)
	for {
		if session.Ping() == nil {
			break
		}

		mLog.Debug("Waiting for device to finish reboot", slog.Duration("passed", passed))
		time.Sleep(rebootCheckInterval)
		passed += rebootCheckInterval
	}

	primary, secondary, err := readImages(session)
	if err != nil {
		errC <- err
		return
	}

	if slices.Compare(primary.Hash, dev.PrimaryImage.Hash) == 0 {
		errC <- fmt.Errorf("Update was rejected")
		return
	}

	if slices.Compare(secondary.Hash, dev.PrimaryImage.Hash) != 0 {
		errC <- fmt.Errorf("Unknown image in primary slot (hash '%x')", secondary.Hash)
		return
	}

	errC <- nil
}

func confirmImage(dev *mcumgr.Device, errC chan<- error) {
	session, err := dev.Transport.AcqSession()
	if err != nil {
		errC <- err
		return
	}
	defer session.Close()

	primary, _, err := readImages(session)
	if err != nil {
		errC <- err
		return
	}

	if err := session.ConfirmImage(primary.Hash); err != nil {
		errC <- fmt.Errorf("Failed to confirm new image")
		return
	}

	dev.PrimaryImage = primary

	errC <- nil
}

func rollback(oldImgHash []byte, dev *mcumgr.Device, errC chan<- error) {
	session, err := dev.Transport.AcqSession()
	if err != nil {
		errC <- err
		return
	}

	primary, secondary, err := readImages(session)
	if err != nil {
		errC <- err
		return
	}

	// First check if device didn't rollback by itself
	if slices.Equal(primary.Hash, oldImgHash) {
		errC <- nil
		return
	}

	if err := session.ConfirmImage(secondary.Hash); err != nil {
		errC <- err
		return
	}

	if err := session.ResetDevice(); err != nil {
		errC <- err
		return
	}
	session.Close()

	for {
		session, err = dev.Transport.AcqSession()
		if err != nil {
			errC <- err
			return
		}
		defer session.Close()

		if session.Ping() == nil {
			// Device rebooted
			break
		}

		time.Sleep(rebootCheckInterval)
	}

	dev.PrimaryImage = secondary
	errC <- nil
}
