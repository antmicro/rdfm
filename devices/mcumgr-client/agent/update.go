package agent

import (
	"errors"
	"fmt"
	"log/slog"
	"rdfm-mcumgr-client/mcumgr"
	"rdfm-mcumgr-client/mcumgr/transport"
	"rdfm-mcumgr-client/rdfm/artifact"
	"slices"
	"time"

	"mynewt.apache.org/newtmgr/nmxact/nmp"
)

const checkInterval = 30 * time.Second

// Main function that pushes an update image down
// to the corresponding device
func RunDeviceUpdate(art *artifact.ZephyrArtifact, dev *mcumgr.Device) error {
	var compatible bool
	for _, v := range art.Compatible {
		if v == dev.Config.DevType {
			compatible = true
		}
	}
	if !compatible {
		return errors.New(fmt.Sprintf("Artifact doesn't support '%s' device type", dev.Config.DevType))
	}

	dev.Log.Debug("Acquiring transport session")
	session, err := dev.Transport.AcqSession()
	if err != nil {
		return err
	}

	dev.Log.Info("Starting update")

	dev.Log.Debug("Writing image")
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
		return errors.New("Can't update using currently running version")
	}

	dev.Log.Debug("Setting image as pending")
	if err := session.SetPendingImage(secondary.Hash); err != nil {
		session.Close()
		return err
	}

	dev.Log.Info("Rebooting")
	if err := session.ResetDevice(); err != nil {
		session.Close()
		return err
	}

	session.Close()
	time.Sleep(checkInterval)

	dev.Log.Debug("Reloading session")
	session, err = dev.Transport.AcqSession()
	if err != nil {
		return err
	}
	defer session.Close()

	// Wait for the device to reboot and bring up SMP server
	passed := checkInterval
	for {
		if session.Ping() == nil {
			break
		}

		dev.Log.Info("Waiting for device to finish reboot", slog.Duration("passed", passed))
		time.Sleep(checkInterval)
		passed += checkInterval
	}

	primary, secondary, err = readImages(session)
	if err != nil {
		return err
	}

	if slices.Compare(primary.Hash, dev.PrimaryImage.Hash) == 0 {
		return errors.New("Update was rejected")
	}

	if slices.Compare(secondary.Hash, dev.PrimaryImage.Hash) != 0 {
		return errors.New(fmt.Sprintf("Unknown image in primary slot (hash '%x')", secondary.Hash))
	}

	if err := session.ConfirmImage(primary.Hash); err != nil {
		return errors.New("Failed to confirm new image")
	}

	dev.PrimaryImage = primary

	return nil
}

func readImages(s transport.Session) (*nmp.ImageStateEntry, *nmp.ImageStateEntry, error) {
	images, err := s.ReadDeviceImages()
	if err != nil {
		return nil, nil, err
	}
	if imgCnt := len(images); imgCnt < 2 {
		return nil, nil, errors.New(fmt.Sprintf("Unexpected amount of images (expected min 2, got %d)", imgCnt))
	}

	return &images[0], &images[1], nil
}
