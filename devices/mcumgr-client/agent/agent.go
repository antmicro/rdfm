package agent

import (
	"bytes"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"rdfm-mcumgr-client/appcfg"
	"rdfm-mcumgr-client/mcumgr"
	"rdfm-mcumgr-client/rdfm"
	"rdfm-mcumgr-client/rdfm/artifact"
	"sync"
	"syscall"
	"time"

	"mynewt.apache.org/newtmgr/nmxact/nmxutil"
)

// Main entrypoint that tries to initialize each device
// and starts its poll update loop
func Run(cfg appcfg.AppConfig, verbose bool) {
	var wg sync.WaitGroup

	log := appLogger(verbose)
	log.Info("Starting client", slog.String("server", cfg.Server))

	exitChs := make(chan chan<- any, len(cfg.Devices))

	log.Debug("Configuring devices", slog.Int("devices", len(cfg.Devices)))
	for _, devcfg := range cfg.Devices {
		go func(devcfg appcfg.DeviceConfig) {
			dLog := log.With(slog.String("device", devcfg.Name))

			// Use global value if device config doesn't specify otherwise
			if devcfg.UpdateInterval == nil {
				devcfg.UpdateInterval = cfg.UpdateInterval
			}

			dev, err := mcumgr.InitDevice(devcfg, cfg.KeyDir, dLog)
			if err != nil {
				logErr("Device setup failed", dLog, err)
				return
			}

			client, err := rdfm.InitClient(cfg.Server)
			if err != nil {
				logErr("RDFM client setup failed", dLog, err)
				return
			}

			attemptRetry := cfg.Retries > 0

			exitCh := make(chan any, 1)
			wg.Add(1)
			go func() {
				defer wg.Done()

				retries := cfg.Retries

				dLog.Info("Configuration successful", slog.String("version", dev.PrimaryImage.Version))
				for {
					if success := runUpdateTask(client, dev); !success && attemptRetry {
						if retries -= 1; retries == 0 {
							dLog.Error(fmt.Sprintf("Device failed to update after %d attempt(s)", cfg.Retries))
							return
						}
					} else {
						retries = cfg.Retries
					}

					select {
					case <-time.After(*cfg.UpdateInterval):
						continue
					case <-exitCh:
						dLog.Info("Exiting")
						return
					}
				}
			}()

			exitChs <- exitCh
		}(devcfg)
	}

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)

	// Wait for exit
	<-sigCh

	log.Info("Exit requested. Waiting for devices")
	for len(exitChs) > 0 {
		c := <-exitChs
		c <- nil
	}
	close(exitChs)

	// Setup forced exit
	go func() {
		timeout := time.Minute
		<-time.After(timeout)
		log.Error(fmt.Sprintf("Forced exit after %v", timeout))
		os.Exit(1)
	}()

	wg.Wait()
}

// Main task that drives the update loop
// It acts as glue that handles RDFM <-> mcumgr connection
func runUpdateTask(client *rdfm.RdfmClient, device *mcumgr.Device) bool {
	device.Log.Debug("Checking for updates")
	update, err := client.UpdateCheck(device)
	if err != nil {
		logErr("Checking for update failed", device.Log, err)
		return false
	}

	// No updates
	if update == nil {
		return true
	}

	device.Log.Info("Fetching new update")
	artBytes, err := client.FetchUpdateArtifact(update)
	if err != nil {
		logErr("Fetching update failed", device.Log, err)
		return false
	}

	art, err := artifact.ExtractArtifact(bytes.NewBuffer(artBytes))
	if err != nil {
		logErr("Artifact extraction failed", device.Log, err)
		return false
	}

	device.Log.Debug("Extracted artifact", slog.String("artifact", art.String()))

	// Pick device updater based on artifact type
	switch a := art.(type) {
	case *artifact.ZephyrArtifact:
		// Update for individual Zephyr device
		if err := RunDeviceUpdate(a, device); err != nil {
			logErr("Failed to update device", device.Log, err)
			return false
		}

		device.Log.Info("Update successful", slog.String("new_version", device.PrimaryImage.Version))
	default:
		device.Log.Error("Unsupported artifact type", slog.String("type", fmt.Sprintf("%T", a)))
	}

	return true
}

func appLogger(verbose bool) *slog.Logger {
	// Disable logging in transport library (newtmgr)
	nmxutil.SetLogLevel(0)

	if verbose {
		//TODO: Use `slog.SetLogLoggerLevel` instead of this when go 1.22 releases
		handler := slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
			Level: slog.LevelDebug,
		})
		return slog.New(handler)
	}

	return slog.Default()
}

func logErr(msg string, l *slog.Logger, e error) {
	l.Error(msg, slog.String("error", e.Error()))
}
