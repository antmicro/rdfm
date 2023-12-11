package daemon

import (
	"log"
	"os"
	"os/signal"
	"sync"
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

	var wg sync.WaitGroup
	var wgNum = 2
	wg.Add(wgNum)

	channel := make(chan os.Signal)
	signal.Notify(channel, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-channel
		for i := 0; i < wgNum; i++ {
			wg.Done()
		}
		device.disconnect()
	}()

	go device.updateCheckerLoop()
	go device.managementWsLoop()
	wg.Wait()

	device.disconnect()

	log.Println("Daemon exited with code:", err)
	return err
}
