package daemon

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
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
	}

	err = device.connect()
	if err != nil {
		log.Println(err)
		return err
	}

	done := make(chan bool, 1)
	channel := make(chan os.Signal)
	signal.Notify(channel, syscall.SIGINT, syscall.SIGTERM)

	go device.updateCheckerLoop(done)
	go device.managementWsLoop(done)

	<-channel
	log.Println("Daemon killed")

	done <- true
	log.Println("Closing daemon...")

	device.disconnect()

	log.Println("Daemon exited with code:", err)
	return err
}
