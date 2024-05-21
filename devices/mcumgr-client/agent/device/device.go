package device

import (
	"fmt"
	"log/slog"
	"time"

	"rdfm-mcumgr-client/mcumgr/transport"
	"rdfm-mcumgr-client/rdfm/api"
	"rdfm-mcumgr-client/rdfm/artifact"

	"mynewt.apache.org/newtmgr/nmxact/nmp"
)

const rebootCheckInterval = 30 * time.Second

type Device interface {
	Version() string
	Metadata() api.DeviceMetadata
	Key() *DeviceKey
	Logger() *slog.Logger
	RunUpdate(artifact.Artifact) error
}

func readImages(s transport.Session) (*nmp.ImageStateEntry, *nmp.ImageStateEntry, error) {
	images, err := s.ReadDeviceImages()
	if err != nil {
		return nil, nil, err
	}
	if imgCnt := len(images); imgCnt < 2 {
		return nil, nil, fmt.Errorf("Unexpected number of images (expected min 2, got %d)", imgCnt)
	}

	return &images[0], &images[1], nil
}
