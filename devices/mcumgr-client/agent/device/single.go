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

type Single struct {
	Cfg    appcfg.DeviceConfig
	Log    *slog.Logger
	DevKey *DeviceKey

	dev *mcumgr.Device
}

func InitSingle(dCfg appcfg.DeviceConfig, cfg *appcfg.AppConfig, log *slog.Logger) (*Single, error) {
	key, err := InitDeviceKey(path.Join(cfg.KeyDir, dCfg.Key), log)
	if err != nil {
		return nil, err
	}

	dev, err := mcumgr.InitDevice(dCfg.Transport, log)
	if err != nil {
		return nil, err
	}

	return &Single{
		Cfg:    dCfg,
		Log:    log,
		DevKey: key,
		dev:    dev,
	}, nil
}

func (s *Single) Version() string {
	return s.dev.PrimaryImage.Version
}

func (s *Single) Metadata() api.DeviceMetadata {
	return api.DeviceMetadata{
		DeviceType:      s.Cfg.DevType,
		SoftwareVersion: s.dev.PrimaryImage.Version,
		MacAddress:      s.Cfg.Id,
	}
}

func (s *Single) Key() *DeviceKey {
	return s.DevKey
}

func (s *Single) Logger() *slog.Logger {
	return s.Log
}

func (s *Single) RunUpdate(a artifact.Artifact) error {
	dev := s.dev
	log := dev.Log

	art, ok := a.(*artifact.ZephyrArtifact)
	if !ok {
		return fmt.Errorf("Unsupported artifact type (%T)", art)
	}

	var compatible bool
	for _, v := range art.Compatible {
		if v == s.Cfg.DevType {
			compatible = true
		}
	}
	if !compatible {
		return fmt.Errorf("Artifact doesn't support '%s' device type", s.Cfg.DevType)
	}

	log.Debug("Acquiring transport session")
	session, err := dev.Transport.AcqSession()
	if err != nil {
		return err
	}

	log.Info("Starting update")

	log.Debug("Writing image")
	if err := session.WriteImage(art.Image); err != nil {
		session.Close()
		return err
	}

	primary, secondary, err := readImages(session)
	if err != nil {
		session.Close()
		return err
	}

	if slices.Compare(primary.Hash, secondary.Hash) == 0 {
		session.Close()
		return fmt.Errorf("Can't update using currently running version")
	}

	log.Debug("Setting image as pending")
	if err := session.SetPendingImage(secondary.Hash); err != nil {
		session.Close()
		return err
	}

	log.Info("Rebooting")
	if err := session.ResetDevice(); err != nil {
		session.Close()
		return err
	}

	session.Close()
	time.Sleep(rebootCheckInterval)

	log.Debug("Reloading session")
	session, err = dev.Transport.AcqSession()
	if err != nil {
		return err
	}
	defer session.Close()

	// Wait for the device to reboot and bring up SMP server
	passed := time.Duration(0)
	for {
		if session.Ping() == nil {
			break
		}

		log.Info("Waiting for device to finish reboot", slog.Duration("passed", passed))
		time.Sleep(rebootCheckInterval)
		passed += rebootCheckInterval
	}

	primary, secondary, err = readImages(session)
	if err != nil {
		return err
	}

	if slices.Compare(primary.Hash, dev.PrimaryImage.Hash) == 0 {
		return fmt.Errorf("Update was rejected")
	}

	if slices.Compare(secondary.Hash, dev.PrimaryImage.Hash) != 0 {
		return fmt.Errorf("Unknown image in primary slot (hash '%x')", secondary.Hash)
	}

	if err := session.ConfirmImage(primary.Hash); err != nil {
		return fmt.Errorf("Failed to confirm new image")
	}

	dev.PrimaryImage = primary

	return nil
}
