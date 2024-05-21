package agent

import (
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"rdfm-mcumgr-client/agent/device"
	"rdfm-mcumgr-client/appcfg"
	"rdfm-mcumgr-client/rdfm"

	"mynewt.apache.org/newtmgr/nmxact/nmxutil"
)

// RDFM client shared between all devices
var rdfmClient *rdfm.RdfmClient

// Main entrypoint
func Run(cfg appcfg.AppConfig, verbose bool) {
	var wg sync.WaitGroup

	log := appLogger(verbose)
	log.Info("Starting client", slog.String("server", cfg.Server))

	// Setup RDFM client
	client, err := rdfm.InitClient(cfg.Server)
	if err != nil {
		logErr("RDFM client setup failed", log, err)
		return
	}
	rdfmClient = client

	exitChs := make(chan chan<- any, len(cfg.Devices)+len(cfg.Groups))

	log.Debug("Configuring devices", slog.Int("devices", len(cfg.Devices)))
	for _, dCfg := range cfg.Devices {

		wg.Add(1)
		go startSingle(dCfg, &cfg, &wg, exitChs, log)
	}

	log.Debug("Configuring groups", slog.Int("groups", len(cfg.Groups)))
	for _, gCfg := range cfg.Groups {

		wg.Add(1)
		go startGroup(gCfg, &cfg, &wg, exitChs, log)
	}

	// Setup exit handler
	go exitSignal(exitChs, log)

	wg.Wait()
	log.Info("All devices stopped")
}

func startSingle(dCfg appcfg.DeviceConfig, cfg *appcfg.AppConfig, wg *sync.WaitGroup, exitChs chan chan<- any, log *slog.Logger) {
	defer wg.Done()
	dLog := log.With(slog.String("device", dCfg.Name))

	// Use global defaults
	if dCfg.UpdateInterval == nil {
		dCfg.UpdateInterval = cfg.UpdateInterval
	}

	dev, err := device.InitSingle(dCfg, cfg, dLog)
	if err != nil {
		logErr("Device setup failed", dLog, err)
		return
	}
	dLog.Info("Configuration successful", slog.String("version", dev.Version()))

	updateLoop(dev, cfg.Retries, *dev.Cfg.UpdateInterval, exitChs)
}

func startGroup(gCfg appcfg.GroupConfig, cfg *appcfg.AppConfig, wg *sync.WaitGroup, exitChs chan chan<- any, log *slog.Logger) {
	defer wg.Done()
	gLog := log.With(slog.String("group", gCfg.Name))

	// Use global defaults
	if gCfg.UpdateInterval == nil {
		gCfg.UpdateInterval = cfg.UpdateInterval
	}

	group, err := device.InitGroup(gCfg, cfg, gLog)
	if err != nil {
		logErr("Group setup failed", gLog, err)
		return
	}
	gLog.Info("Configuration successful", slog.String("version", group.Version()), slog.Int("members", group.Members()))

	updateLoop(group, cfg.Retries, *group.Cfg.UpdateInterval, exitChs)
}

func exitSignal(exitChs chan chan<- any, log *slog.Logger) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)

	<-sigCh

	log.Info("Requesting exit from devices...")
	for len(exitChs) > 0 {
		c := <-exitChs
		c <- nil
	}
	close(exitChs)

	// Force exit after timeout passes
	<-time.After(time.Minute)
	log.Error("Forced exit")
	os.Exit(1)
}

func appLogger(verbose bool) *slog.Logger {
	// Disable logging in transport library (newtmgr)
	nmxutil.SetLogLevel(0)

	if verbose {
		slog.SetLogLoggerLevel(slog.LevelDebug)
	}

	return slog.Default()
}

func logErr(msg string, l *slog.Logger, e error) {
	l.Error(msg, slog.String("error", e.Error()))
}
