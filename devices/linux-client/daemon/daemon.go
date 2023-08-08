package daemon

import (
	"bytes"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"mime/multipart"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	libcli "github.com/urfave/cli/v2"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	"github.com/antmicro/rdfm/daemon/proxy"

	netUtils "github.com/antmicro/rdfm/daemon/net_utils"
	packages "github.com/antmicro/rdfm/daemon/packages"
	requests "github.com/antmicro/rdfm/daemon/requests"
)

const HEADER_LEN = 10

type Device struct {
	name          string
	fileMetadata  string
	encrypt_proxy bool
	socket        net.Conn
	metadata      map[string]interface{}
	caps          capabilities.DeviceCapabilities
	macAddr       string
	rdfmCtx       *app.RDFM
}

func (d Device) recv() (requests.Request, error) {
	hdr, err := netUtils.RecvExactly(d.socket, HEADER_LEN)

	if err != nil {
		log.Println("Error receiving header:", err)
		return nil, err
	}
	msg_len, err := strconv.Atoi(strings.TrimSpace(string(hdr[:])))
	if err != nil {
		log.Println(err)
		return nil, err
	}

	msg, err := netUtils.RecvExactly(d.socket, msg_len)
	if err != nil {
		if err != io.EOF {
			log.Println("Error receiving msg:", err)
			return nil, err
		}
	}

	parsed, err := requests.Parse(string(msg[:]))
	if err != nil {
		return nil, err
	}

	return parsed, nil
}

func (d Device) send(msg requests.Request) error {
	s_msg, err := json.Marshal(msg)
	if err != nil {
		log.Println(err)
		return err
	}

	n, err := d.socket.Write([]byte(fmt.Sprintf("%10d%s", len(s_msg), s_msg)))
	if n != HEADER_LEN+len(s_msg) {
		log.Println(err)
		return err
	}
	if err != nil {
		log.Println(err)
		return err
	}
	return nil
}

func (d *Device) startClient() error {
	d.checkUpdatesPeriodically()
	err := d.communicationLoop()
	if err != nil {
		log.Println("Error running client", err)
		return err
	}
	return nil
}

func (d *Device) communicationLoop() error {
	for {
		req, err := d.recv()
		if err != nil {
			log.Println(err)
			return err
		}
		res, err := d.handleRequest(req)
		if err != nil {
			log.Println(err)
			return err
		}

		if res != nil {
			err := d.send(res)
			if err != nil {
				log.Println(err)
				return err
			}
		}
	}
}

func (d Device) connect() error {
	// Try to get JWT token from config
	token := d.rdfmCtx.Configuration.TenantToken
	// Try to auth using token
	if token != "" {
		log.Println("Token found, trying to auth...")
		d.send(requests.Auth{
			Method: "auth_token",
			Jwt:    token,
		})
		res, err := d.recv()
		if err != nil {
			log.Println("Error sending token", err)
			return err
		}

		switch r := res.(type) {
		case requests.Alert:
			log.Printf("alert: %v %T", r.Alert, r.Alert)
			log.Println(r)
			msg, present := r.Alert["message"]
			if present {
				log.Println(msg)
				return nil
			}
			msg, present = r.Alert["error"]
			if present {
				log.Println("Failed to connect using token", msg)
			}
		default:
			err = errors.New("unknown server response")
			log.Println(err)
			return err
		}
	} else {
		log.Println("No TenantToken in configuration")
	}

	// JWT auth failed/no token
	log.Println("Registering device...")
	err := d.send(requests.Register{
		Method: "register",
		Client: requests.Client{
			Name:         d.name,
			Group:        requests.DeviceType,
			Capabilities: d.caps,
			MacAddress:   d.macAddr,
		},
	})
	if err != nil {
		return err
	}
	res, err := d.recv()
	if err != nil {
		return err
	}
	switch r := res.(type) {
	// Got JWT token from server
	case requests.Auth:
		d.rdfmCtx.Configuration.TenantToken = r.Jwt
		log.Println("Got JWT token!")
		//TODO: Save it in config files - currently no function to do it
		// besides explict calling function on specified file
	case requests.Alert:
		log.Println(r.Alert)
		return errors.New("registration refused")
	}

	return nil
}

func (d *Device) handleRequest(request requests.Request) (requests.Request, error) {
	if !requests.CanHandleRequest(request, d.caps) {
		log.Println("cannot handle request")
		res := requests.Alert{
			Alert: map[string]interface{}{
				"error": "Device cannot handle request",
			},
		}
		return res, nil
	}

	log.Printf("Handling %T request...\n", request)
	switch r := request.(type) {
	case requests.Proxy:
		addr, err := netUtils.AddrWithoutPort(d.socket.LocalAddr().String())
		if err != nil {
			log.Println("Failed to get server's proxy address")
			return nil, err
		}
		if d.encrypt_proxy {
			go proxy.ConnectReverseEncrypted(addr, r.Port,
				d.rdfmCtx.Configuration.ServerCertificate)
		} else {
			go proxy.ConnectReverseUnencrypted(addr, r.Port)
		}

	case requests.Update:
		err := d.updateMetadata()
		if err != nil {
			log.Println("Failed to update metadata", err)
			return nil, err
		}
		metadata, err := json.Marshal(d.metadata)
		if err != nil {
			log.Println("Error serializing metadata", err)
			return nil, err
		}

		log.Println("Sending metadata", string(metadata[:]))

		return requests.Metadata{
			Method:   "metadata",
			Metadata: d.metadata,
		}, nil
	case requests.Download:
		// Download to device
		log.Printf("Received download request of file %s", r.FilePath)

		out, err := os.Create(r.FilePath)
		if err != nil {
			log.Printf("Failed to create output file %s\n", r.FilePath)
			return nil, err
		}
		defer out.Close()
		resp, err := http.Get(r.Url)
		if err != nil {
			log.Println("Failed to get file from url", err)
			return nil, err
		}
		defer resp.Body.Close()
		_, err = io.Copy(out, resp.Body)
		if err != nil {
			err := fmt.Errorf("failed to save file %w", err)
			return nil, err
		}
		log.Println("Downloaded file")
	case requests.Upload:
		// Upload from device
		log.Printf("Received upload request of file %s", r.FilePath)
		endpoint := fmt.Sprintf("%s/upload", d.rdfmCtx.Configuration.ServerURL)
		fileSent := false

		body := &bytes.Buffer{}
		writer := multipart.NewWriter(body)
		writer.WriteField("jwt", d.rdfmCtx.Configuration.TenantToken)
		writer.WriteField("file_path", r.FilePath)

		file, err := os.Open(r.FilePath)
		if err != nil {
			log.Println("Failed to open file", err)
			writer.WriteField("error", "Failed to open file")
		} else {
			fileContents, err := ioutil.ReadAll(file)
			if err != nil {
				log.Println("Failed to read file", err)
				writer.WriteField("error", "Failed to read file")
			} else {
				part, err := writer.CreateFormFile("file", filepath.Base(r.FilePath))
				if err != nil {
					log.Println("Failed to create form file", err)
				}
				part.Write(fileContents)
				fileSent = true
			}
		}
		file.Close()
		writer.Close()

		req, _ := http.NewRequest("POST", endpoint, body)
		req.Header.Add("Content-Type", writer.FormDataContentType())
		client := &http.Client{}
		_, err = client.Do(req)
		if err != nil || !fileSent {
			log.Println("Failed to upload file", r.FilePath, err)
		} else {
			log.Println("Uploaded file", r.FilePath)
		}
	}

	return nil, nil
}

func (d *Device) updateMetadata() error {
	metadata, err := os.ReadFile(d.fileMetadata)
	if err != nil {
		log.Println("Unable to read metadata from file:",
			d.fileMetadata, err)
		return err
	}
	err = json.Unmarshal(metadata, &d.metadata)
	if err != nil {
		log.Println("Unable to parse read metadata", err)
		return err
	}
	log.Println("Read metadata from", d.fileMetadata)
	return nil
}

func (d Device) checkUpdatesPeriodically() {
	devType, err := d.rdfmCtx.GetCurrentDeviceType()
	if err != nil {
		log.Println("Error getting current device type", err)
		return
	}
	swVer, err := d.rdfmCtx.GetCurrentArtifactName()
	if err != nil {
		log.Println("Error getting current software version", err)
		return
	}

	go func() {
		for {
			time.Sleep(
				time.Duration(d.rdfmCtx.Configuration.UpdatePollIntervalSeconds) *
					time.Second)
			log.Println("Checking updates...")
			metadata := map[string]string{
				"rdfm.hardware.devtype": devType,
				"rdfm.software.version": swVer,
			}
			serializedMetadata, err := json.Marshal(metadata)
			if err != nil {
				log.Println("Failed to serialize metadata", err)
				return
			}
			res, err := http.Post(
				fmt.Sprintf("%s/api/v1/update/check", d.rdfmCtx.Configuration.ServerURL),
				"application/json",
				bytes.NewBuffer(serializedMetadata),
			)
			if err != nil {
				log.Println("Failed to check updates", err)
				return
			}

			switch res.StatusCode {
			case 200:
				log.Println("An update is available")
				var pkg packages.Package
				bodyBytes, err := io.ReadAll(res.Body)
				defer res.Body.Close()
				if err != nil {
					log.Println("Failed to get package metadata from response body", err)
					return
				}
				err = json.Unmarshal(bodyBytes, &pkg)
				if err != nil {
					log.Println("Failed to deserialize package metadata", err)
					return
				}

				log.Printf("Installing package from %s...\n", pkg.Uri)
				err = d.rdfmCtx.InstallArtifact(pkg.Uri)
				if err != nil {
					log.Println("Failed to install package",
						pkg.Id, err)
					// TODO: Do something in case of failure
				}

			case 204:
				log.Println("No updates are available")
			case 400:
				log.Println("Device metadata is missing device type and/or software version")
			case 401:
				log.Println("Device did not provide authorization data, or the authorization has expired")
			}
		}
		log.Println("Stopped checking for updates")
	}()
}

func Run(c *libcli.Context) error {

	host := c.String("host")
	port := c.Int("port")
	name := c.String("name")
	fileMetadata := c.String("file-metadata")
	notEncrypted := c.Bool("no-ssl")
	config := c.String("config")

	ctx, err := app.NewRdfmContext()
	if err != nil {
		log.Fatal("Failed to create RDFM context", err)
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
		cert, err = os.ReadFile(ctx.Configuration.ServerCertificate)
		if err != nil {
			log.Fatal("Failed to read certificate file:", err)
			return err
		} else {
			conf := &tls.Config{}
			os.Setenv("SSL_CERT_DIR", filepath.Dir(string(ctx.Configuration.ServerCertificate)))
			log.Printf("Set $SSL_CERT_DIR to \"%s\"\n", os.Getenv("SSL_CERT_DIR"))
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
		name:          name,
		fileMetadata:  fileMetadata,
		socket:        conn,
		encrypt_proxy: !notEncrypted,
		metadata:      nil,
		caps:          caps,
		macAddr:       ourMacAddr,
		rdfmCtx:       ctx,
	}

	err = device.connect()
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
