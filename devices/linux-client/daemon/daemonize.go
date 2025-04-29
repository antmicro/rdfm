package daemon

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"

	log "github.com/sirupsen/logrus"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	"github.com/antmicro/rdfm/telemetry"
	libcli "github.com/urfave/cli/v2"
)

func Daemonize(c *libcli.Context) error {
	name := c.String("name")
	fileMetadata := c.String("file-metadata")
	config := c.String("config")

	ctx, err := app.NewRdfmContext()
	if err != nil {
		log.Fatal("Failed to create RDFM context, ", err)
		return err
	}

	caps, err := capabilities.LoadCapabilities(config)
	if err != nil {
		log.Fatal("Failed to load config:", err)
		return err
	}

	device := Device{
		name:         name,
		fileMetadata: fileMetadata,
		metadata:     nil,
		caps:         caps,
		rdfmCtx:      ctx,
		logManager:   telemetry.MakeLogManager(),
	}

	err = device.setupConnection()
	if err != nil {
		log.Println(err)
		return err
	}
	err = device.setupActionRunner()
	if err != nil {
		log.Errorln("Failed to setup action runner:", err)
		return err
	}

	channel := make(chan os.Signal)
	signal.Notify(channel, syscall.SIGINT, syscall.SIGTERM)

	cancelCtx, cancelFunc := context.WithCancel(context.Background())

	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer func() {
			log.Infoln("Finished updateCheckerLoop.")
			wg.Done()
		}()
		log.Infoln("Starting updateCheckerLoop...")
		device.updateCheckerLoop(cancelCtx)
	}()

	wg.Add(1)
	go func() {
		defer func() {
			log.Infoln("Finished telemtryLoop.")
			wg.Done()
		}()
		log.Infoln("Starting telemtryLoop...")
		device.telemetryLoop(cancelCtx)
	}()

	wg.Add(1)
	go func() {
		defer func() {
			log.Println("Finished managementWsLoop.")
			wg.Done()
		}()
		log.Infoln("Starting managementWsLoop...")
		device.managementWsLoop(cancelCtx)
	}()

	<-channel
	log.Println("Daemon killed")

	cancelFunc()
	log.Println("Closing daemon...")
	wg.Wait()

	exitInfo := "Daemon exited"
	if err != nil {
		exitInfo = exitInfo + fmt.Sprintf(" with error: %v", err)
	}
	log.Println(exitInfo)
	return err
}
