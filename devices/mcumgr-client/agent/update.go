package agent

import (
	"bytes"
	"log/slog"
	"rdfm-mcumgr-client/agent/device"
	"rdfm-mcumgr-client/rdfm/artifact"
	"time"
)

func updateLoop(dev device.Device, maxRetries uint, delay time.Duration, exitChs chan chan<- any) {
	log := dev.Logger()

	exitC := make(chan any, 1)
	exitChs <- exitC

	alwaysRetry := maxRetries == 0
	updateAttempt := uint(1)
	for {
		if ok := runUpdateTask(dev); !ok {
			if !alwaysRetry && updateAttempt >= maxRetries {
				log.Error("Retry limit reached", slog.Uint64("attempts", uint64(updateAttempt)))
				return
			}

			var maxAttempts slog.Attr
			if !alwaysRetry {
				maxAttempts = slog.Uint64("max", uint64(maxRetries))
			}
			log.Warn("Update attempt failed", slog.Uint64("attempt", uint64(updateAttempt)), maxAttempts)
			updateAttempt += 1

		} else {
			updateAttempt = 1
		}

		select {
		case <-time.After(delay):
			continue
		case <-exitC:
			log.Info("Exiting")
			return
		}
	}
}

// Main task that drives the update loop
// It acts as glue that handles RDFM <-> mcumgr connection
func runUpdateTask(device device.Device) bool {
	log := device.Logger()

	log.Debug("Checking for updates")
	update, err := rdfmClient.UpdateCheck(device)
	if err != nil {
		logErr("Checking for update failed", log, err)
		return false
	}

	// No updates
	if update == nil {
		return true
	}

	log.Info("Fetching new update")
	artBytes, err := rdfmClient.FetchUpdateArtifact(update)
	if err != nil {
		logErr("Fetching update failed", log, err)
		return false
	}

	art, err := artifact.ExtractArtifact(bytes.NewBuffer(artBytes))
	if err != nil {
		logErr("Artifact extraction failed", log, err)
		return false
	}

	log.Debug("Extracted artifact", slog.String("artifact", art.String()))

	// Pick device updater based on artifact type
	if err := device.RunUpdate(art); err != nil {
		logErr("Failed to push update to device", log, err)
		return false
	}

	log.Info("Update successful", slog.String("new_version", device.Version()))
	return true
}
