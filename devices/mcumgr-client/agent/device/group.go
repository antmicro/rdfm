package device

import (
	"fmt"
	"log/slog"
	"path"
	"slices"
	"time"

	"rdfm-mcumgr-client/appcfg"
	"rdfm-mcumgr-client/mcumgr"
	"rdfm-mcumgr-client/mcumgr/transport"
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
		target      string
		dev         *mcumgr.Device
		selfConfirm bool

		rollbackHash []byte
	}

	gWithSessionCb     func(*member, transport.Session) error
	gLoopWithSessionCb func(*member, transport.Session) (bool, error)
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

		rollbackHash := slices.Clone(dev.PrimaryImage.Hash)

		members = append(members, member{
			target:       m.Device,
			dev:          dev,
			selfConfirm:  m.SelfConfirm,
			rollbackHash: rollbackHash,
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

	log.Info("Starting update")

	if err := g.runWithSession(func(m *member, session transport.Session) error {
		log := m.dev.Log
		image := art.Images[m.target]

		log.Debug("Writing image")
		if err := session.WriteImage(image.Data); err != nil {
			return err
		}

		primary, secondary, err := readImages(session)
		if err != nil {
			return err
		}

		if slices.Equal(primary.Hash, secondary.Hash) {
			return fmt.Errorf("Can't update using currently running version")
		}

		return nil
	}); err != nil {
		return err
	}

	log.Debug("Setting images to pending")
	if err := g.runWithSession(g.setPending); err != nil {
		return err
	}

	log.Info("Rebooting")
	if err := g.runWithSession(g.reboot); err != nil {
		return err
	}
	time.Sleep(rebootCheckInterval)
	g.loopWithSession(g.finishReboot)

	log.Debug("Confirming image")
	if err := g.loopWithSession(g.confirm); err != nil {
		// At least one confirmation failed -> rollback entire group
		log.Warn("Update failed. Rolling back")
		if err := g.runWithSession(g.rollback); err != nil {
			log.Error("Rollback failed")
			return err
		}

		time.Sleep(rebootCheckInterval)
		g.loopWithSession(g.finishReboot)
		log.Info("Rollback finished", slog.String("restored_version", g.currVersion))

		return err
	}

	for _, m := range g.members {
		m.rollbackHash = slices.Clone(m.dev.PrimaryImage.Hash)
	}
	g.currVersion = g.members[0].dev.PrimaryImage.Version

	return nil
}

// Runs provided callback with each group member in a separate goroutine
//
// Provided transport session is released automatically
// after callback finishes
func (g *Group) runWithSession(cb gWithSessionCb) error {
	errC := make(chan error)
	for _, m := range g.members {
		go func() {
			session, err := m.dev.Transport.AcqSession()
			if err != nil {
				errC <- err
				return
			}
			defer session.Close()

			errC <- cb(&m, session)
		}()
	}

	var err error
	for range g.members {
		if e := <-errC; e != nil {
			err = e
		}
	}
	return err
}

func (g *Group) loopWithSession(cb gLoopWithSessionCb) error {
	errC := make(chan error)
	for _, m := range g.members {
		go func() {
			for {
				session, err := m.dev.Transport.AcqSession()
				if err != nil {
					errC <- err
					return
				}

				if end, err := cb(&m, session); end {
					session.Close()
					errC <- err
					return
				}

				session.Close()
				time.Sleep(rebootCheckInterval)
			}
		}()
	}

	var err error
	for range g.members {
		if e := <-errC; e != nil {
			err = e
		}
	}
	return err
}

func (*Group) setPending(m *member, session transport.Session) error {
	log := m.dev.Log

	_, secondary, err := readImages(session)
	if err != nil {
		return err
	}

	log.Debug("Setting image as pending")
	if err := session.SetPendingImage(secondary.Hash); err != nil {
		return err
	}

	return nil
}

func (*Group) reboot(m *member, session transport.Session) error {
	log := m.dev.Log

	log.Debug("Rebooting")
	return session.ResetDevice()
}

func (*Group) finishReboot(m *member, session transport.Session) (bool, error) {
	log := m.dev.Log

	if session.Ping() != nil {
		log.Debug("Waiting for device reboot")
		return false, nil
	}
	return true, nil
}

func (g *Group) confirm(m *member, session transport.Session) (bool, error) {
	if m.selfConfirm {
		return g.deviceConfirm(m, session)
	}
	return g.manualConfirm(m, session)
}

func (*Group) deviceConfirm(m *member, session transport.Session) (bool, error) {
	log := m.dev.Log

	primary, _, err := readImages(session)
	if err != nil {
		return false, nil
	}

	if !primary.Confirmed {
		log.Debug("Waiting for device to confirm update")
		return false, nil
	}

	if slices.Equal(primary.Hash, m.dev.PrimaryImage.Hash) {
		return true, fmt.Errorf("Update rejected")
	}

	m.dev.PrimaryImage = primary
	return true, nil
}

func (g *Group) manualConfirm(m *member, session transport.Session) (bool, error) {
	log := m.dev.Log

	primary, _, err := readImages(session)
	if err != nil {
		return true, err
	}

	if slices.Equal(primary.Hash, m.dev.PrimaryImage.Hash) {
		return true, fmt.Errorf("Update rejected")
	}

	log.Debug("Manually confirming image")
	if err := session.ConfirmImage(primary.Hash); err != nil {
		return true, fmt.Errorf("Failed to confirm new image")
	}

	m.dev.PrimaryImage = primary
	return true, nil
}

func (*Group) rollback(m *member, session transport.Session) error {
	primary, secondary, err := readImages(session)
	if err != nil {
		return err
	}

	if slices.Equal(primary.Hash, m.rollbackHash) {
		m.dev.PrimaryImage = primary
		return nil
	}

	if !slices.Equal(secondary.Hash, m.rollbackHash) {
		return fmt.Errorf("Unknown image in secondary slot")
	}

	if err := session.ConfirmImage(secondary.Hash); err != nil {
		return err
	}

	m.dev.PrimaryImage = primary
	return session.ResetDevice()
}
