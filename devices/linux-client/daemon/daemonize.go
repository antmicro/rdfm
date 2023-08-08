package daemon

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"log"
	"net"
	"os"
	"path/filepath"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	netUtils "github.com/antmicro/rdfm/daemon/net_utils"
	libcli "github.com/urfave/cli/v2"
)

func Daemonize(c *libcli.Context) error {
	host := c.String("host")
	port := c.Int("port")
	name := c.String("name")
	fileMetadata := c.String("file-metadata")
	notEncrypted := c.Bool("no-ssl")
	config := c.String("config")
	jwtAuth := !c.Bool("no-jwt-auth")

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

	var conn net.Conn
	var cert []byte
	if !notEncrypted {
		cert, err = os.ReadFile(ctx.RdfmConfig.ServerCertificate)
		if err != nil {
			log.Fatal("Failed to read certificate file: ",
				ctx.RdfmConfig.ServerCertificate, err)
			return err
		} else {
			conf := &tls.Config{}
			os.Setenv("SSL_CERT_DIR",
				filepath.Dir(string(ctx.RdfmConfig.ServerCertificate)))
			log.Printf("Set $SSL_CERT_DIR to \"%s\"\n",
				os.Getenv("SSL_CERT_DIR"))
			caCertPool := x509.NewCertPool()
			caCertPool.AppendCertsFromPEM(cert)
			conf = &tls.Config{
				RootCAs: caCertPool,
			}

			if len(cert) > 0 {
				log.Println("Creating TLS socket")
				conn, err = tls.Dial(
					"tcp",
					fmt.Sprintf("%s:%d", host, port),
					conf,
				)
				if err != nil {
					return err
				}
			}
		}
	} else {
		log.Println("Creating TCP socket")
		conn, err = net.Dial(
			"tcp",
			fmt.Sprintf("%s:%d", host, port),
		)
	}
	if err != nil {
		log.Println("Failed to create socket", err)
		return err
	}

	ourMacAddr, err := netUtils.ConnectedMacAddr(conn)
	if err != nil {
		return err
	} else {
		log.Println("Our MAC addr:", ourMacAddr)
	}

	if err != nil {
		log.Fatal("Failed to connect to the server")
		return err
	}

	device := Device{
		name:         name,
		fileMetadata: fileMetadata,
		encryptProxy: !notEncrypted,
		socket:       conn,
		metadata:     nil,
		caps:         caps,
		macAddr:      ourMacAddr,
		rdfmCtx:      ctx,
		authToken:    &AuthToken{},
	}

	err = device.connect(jwtAuth)
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
