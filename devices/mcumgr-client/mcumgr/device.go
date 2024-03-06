package mcumgr

import (
	"errors"
	"log/slog"
	"path"

	"rdfm-mcumgr-client/appcfg"
	"rdfm-mcumgr-client/mcumgr/transport"

	"mynewt.apache.org/newtmgr/nmxact/nmp"
)

type Device struct {
	Config    appcfg.DeviceConfig
	Transport transport.Transport
	Key       *DeviceKey

	PrimaryImage *nmp.ImageStateEntry

	Log *slog.Logger
}

func InitDevice(cfg appcfg.DeviceConfig, keyBasePath string, log *slog.Logger) (*Device, error) {
	log.Debug("Initializing device transport", slog.String("type", cfg.Transport.Type))
	transport, err := transport.InitTransport(cfg.Transport)
	if err != nil {
		return nil, err
	}

	// Try to load software information from the device
	log.Debug("Acquiring device session")
	session, err := transport.AcqSession()
	if err != nil {
		return nil, err
	}
	defer session.Close()

	log.Debug("Reading images")
	images, err := session.ReadDeviceImages()
	if err != nil {
		return nil, err
	}

	if len(images) < 1 {
		return nil, errors.New("Device should have at least one image")
	}

	if img := images[0]; !img.Confirmed {
		log.Warn("Device with pending primary image. Trying to confirm")

		if err := session.ConfirmImage(img.Hash); err != nil {
			return nil, err
		}
	}

	devKey, err := InitDeviceKey(path.Join(keyBasePath, cfg.Key), log)
	if err != nil {
		return nil, err
	}

	return &Device{
		Config:       cfg,
		Transport:    transport,
		Key:          devKey,
		PrimaryImage: &images[0],
		Log:          log,
	}, nil
}
