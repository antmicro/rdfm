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
	Single struct {
		Cfg    appcfg.DeviceConfig
		Log    *slog.Logger
		DevKey *DeviceKey

		dev *mcumgr.Device
	}
	sLoopWithSessionCb func(transport.Session) (bool, error)
)

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
	log := s.dev.Log

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

	if err := s.flashUpdate(art); err != nil {
		return err
	}
	time.Sleep(rebootCheckInterval)

	s.loopWithSession(s.finishReboot)

	log.Debug("Confirming image")
	if s.Cfg.SelfConfirm {
		return s.loopWithSession(s.deviceFinalize)
	}

	return s.manualFinalize()
}

func (s *Single) loopWithSession(cb sLoopWithSessionCb) error {
	for {
		session, err := s.dev.Transport.AcqSession()
		if err != nil {
			return err
		}

		if end, err := cb(session); end {
			session.Close()
			return err
		}

		session.Close()
		time.Sleep(rebootCheckInterval)
	}
}

func (s *Single) flashUpdate(art *artifact.ZephyrArtifact) error {
	log := s.dev.Log

	log.Debug("Acquiring transport session")
	session, err := s.dev.Transport.AcqSession()
	if err != nil {
		return err
	}
	defer session.Close()

	log.Info("Starting update")

	log.Debug("Writing image")
	if err := session.WriteImage(art.Image); err != nil {
		return err
	}

	primary, secondary, err := readImages(session)
	if err != nil {
		return err
	}

	if slices.Equal(primary.Hash, secondary.Hash) {
		return fmt.Errorf("Can't update using currently running version")
	}

	log.Debug("Setting image as pending")
	if err := session.SetPendingImage(secondary.Hash); err != nil {
		return err
	}

	log.Info("Rebooting")
	return session.ResetDevice()
}

func (s *Single) finishReboot(session transport.Session) (bool, error) {
	log := s.dev.Log

	if session.Ping() != nil {
		log.Debug("Waiting for device reboot")
		return false, nil
	}
	return true, nil
}

func (s *Single) deviceFinalize(session transport.Session) (bool, error) {
	log := s.dev.Log

	primary, _, err := readImages(session)
	if err != nil {
		return true, err
	}

	if !primary.Confirmed {
		log.Debug("Waiting for device to confirm update")
		return false, nil
	}

	if slices.Equal(primary.Hash, s.dev.PrimaryImage.Hash) {
		return true, fmt.Errorf("Update rejected")
	}

	s.dev.PrimaryImage = primary
	return true, nil
}

func (s *Single) manualFinalize() error {
	log := s.dev.Log
	session, err := s.dev.Transport.AcqSession()
	if err != nil {
		return err
	}
	defer session.Close()

	primary, _, err := readImages(session)
	if err != nil {
		return err
	}

	if slices.Equal(primary.Hash, s.dev.PrimaryImage.Hash) {
		return fmt.Errorf("Update rejected")
	}

	log.Debug("Manually confirming image")
	if err := session.ConfirmImage(primary.Hash); err != nil {
		return fmt.Errorf("Failed to confirm new image")
	}

	s.dev.PrimaryImage = primary
	return nil
}
