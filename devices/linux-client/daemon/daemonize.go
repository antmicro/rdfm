package daemon

import (
	"log"
	"fmt"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	libcli "github.com/urfave/cli/v2"
)

func Daemonize(c *libcli.Context) error {
	host := c.String("host")
	port := c.Int("port")
	name := c.String("name")
	fileMetadata := c.String("file-metadata")
	notEncrypted := c.Bool("no-ssl")
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
		encryptProxy: !notEncrypted,
		metadata:     nil,
		caps:         caps,
		rdfmCtx:      ctx,
		authToken:    &AuthToken{},
	}

	err = device.connect(fmt.Sprintf("%s:%d", host, port))
	if err != nil {
		log.Println(err)
		return err
	}
	err = device.startClient()
	if err != nil {
		log.Println(err)
		return err
	}
	log.Println("Daemon exited")
	return nil
}
