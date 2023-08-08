package daemon

import (
	"bytes"
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

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	"github.com/antmicro/rdfm/daemon/proxy"

	netUtils "github.com/antmicro/rdfm/daemon/net_utils"
	packages "github.com/antmicro/rdfm/daemon/packages"
	requests "github.com/antmicro/rdfm/daemon/requests"
)

const HEADER_LEN = 10
const MSG_RECV_TIMEOUT_INTERVALS = 10
const MSG_RECV_INTERVAL_S = 1

type AuthToken struct {
	value string
	// Path to file where auth token is saved
	file string
}

type Device struct {
	name         string
	fileMetadata string
	encryptProxy bool
	socket       net.Conn
	metadata     map[string]interface{}
	caps         capabilities.DeviceCapabilities
	macAddr      string
	rdfmCtx      *app.RDFM
	authToken    *AuthToken
}

func recv(s net.Conn) ([]byte, error) {
	hdr, err := netUtils.RecvExactly(s, HEADER_LEN)

	if err != nil {
		log.Println("Error receiving header:", err)
		return nil, err
	}
	msg_len, err := strconv.Atoi(strings.TrimSpace(string(hdr[:])))
	if err != nil {
		log.Println(err)
		return nil, err
	}

	msg, err := netUtils.RecvExactly(s, msg_len)
	if err != nil {
		if err != io.EOF {
			log.Println("Error receiving msg:", err)
			return nil, err
		}
	}
	return msg, nil
}

func (d Device) recv() (requests.Request, error) {
	var msg []byte
	var err error

	for i := 0; i < MSG_RECV_TIMEOUT_INTERVALS; i++ {
		msg, err = recv(d.socket)
		if err != nil {
			return nil, err
		}
		if len(msg) > 0 {
			break
		}
		time.Sleep(MSG_RECV_INTERVAL_S * time.Second)
	}
	if len(msg) == 0 {
		return nil, errors.New("server response timeout")
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

func (d *Device) loadAuthToken() error {
	authToken, err := os.ReadFile(d.rdfmCtx.RdfmConfig.AuthTokenFile)
	if len(authToken) > 0 {
		log.Println("Found auth token: ", authToken)
		if err == nil {
			d.authToken = &AuthToken{
				value: string(authToken),
				file:  app.RdfmTokenPath,
			}
		}
	} else {
		log.Println("Auth token not found in path provided in config, ",
			d.rdfmCtx.RdfmConfig.AuthTokenFile)
		authToken, err = os.ReadFile(app.RdfmTokenPath)
		if err != nil {
			log.Println("Auth token not found in default path, ",
				app.RdfmTokenPath)
			return err
		}
		log.Println("Auth token found in default path")
		d.authToken = &AuthToken{
			value: string(authToken),
			file:  app.RdfmTokenPath,
		}
	}
	return nil
}

func (d *Device) connect(jwtAuth bool) error {
	file, err := os.OpenFile(app.RdfmTokenPath, os.O_CREATE, 0600)
	if err != nil {
		return err
	}
	d.authToken = &AuthToken{
		file:  file.Name(),
		value: "",
	}
	if jwtAuth {
		log.Println("Trying to connect using auth token")
		if err := d.loadAuthToken(); err != nil {
			log.Println("Error loading auth token, ", err)
			if err != nil {
				log.Println("Error creating file for auth token, ", d.authToken.file)
				return err
			}
		}
		// Try to auth using token
		if d.authToken.value != "" {
			log.Println("Token found, trying to auth...")
			d.send(requests.Auth{
				Method: "auth_token",
				Jwt:    d.authToken.value,
			})
			res, err := d.recv()
			if err != nil {
				log.Println("Error sending token", err)
			}

			switch r := res.(type) {
			case requests.Alert:
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
				log.Println(err, res)
				return err
			}
		} else {
			log.Println("No AuthToken in configuration")
		}
	}

	// JWT auth failed/no token
	log.Println("Registering device...")
	err = d.send(requests.Register{
		Method: "register",
		Client: requests.Client{
			Name:         d.name,
			Group:        requests.DeviceType,
			Capabilities: d.caps,
			MacAddress:   d.macAddr,
		},
	})
	if err != nil {
		log.Println("Error sending register request to server: ", err)
		return err
	}
	res, err := d.recv()
	if err != nil {
		log.Println("Error receiving response to register request from server: ", err)
		return err
	}
	switch r := res.(type) {
	// Got JWT token from server
	case requests.Auth:
		d.authToken.value = r.Jwt
		log.Println("Got auth token!")

		err = os.WriteFile(d.authToken.file, []byte(r.Jwt), 0600)
		if err != nil {
			log.Println("Error saving auth token to file ", d.authToken.file)
			return err
		}
	case requests.Alert:
		log.Println(r.Alert)
		return errors.New("registration refused")
	default:
		err = errors.New("received unknown response")
		log.Println(err, res)
		return err
	}
	log.Println("Connected to the server")

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
		if d.encryptProxy {
			go proxy.ConnectReverseEncrypted(addr, r.Port,
				d.rdfmCtx.RdfmConfig.ServerCertificate)
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
		log.Println("Received download request of file ", r.FilePath)
		log.Println("Downloading file from ", r.Url)

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
		endpoint := fmt.Sprintf("%s/upload", d.rdfmCtx.RdfmConfig.ServerURL)
		log.Println("Uploading file to ", endpoint)
		fileSent := false

		body := &bytes.Buffer{}
		writer := multipart.NewWriter(body)
		writer.WriteField("jwt", d.authToken.value)
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
			log.Println("Checking updates...")
			metadata := map[string]string{
				"rdfm.hardware.devtype": devType,
				"rdfm.software.version": swVer,
				"rdfm.hardware.macaddr": d.macAddr,
			}
			log.Println("Metadata to check updates: ", metadata)
			serializedMetadata, err := json.Marshal(metadata)
			if err != nil {
				log.Println("Failed to serialize metadata", err)
				return
			}
			endpoint := fmt.Sprintf("%s/api/v1/update/check",
				d.rdfmCtx.RdfmConfig.ServerURL)
			res, err := http.Post(endpoint, "application/json",
				bytes.NewBuffer(serializedMetadata),
			)
			if err != nil {
				log.Println("Failed to check updates from ", err)
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
			update_duration := time.Duration(d.rdfmCtx.RdfmConfig.UpdatePollIntervalSeconds) * time.Second
			log.Printf("Next update check in %s\n", update_duration)
			time.Sleep(time.Duration(update_duration))
		}
		log.Println("Stopped checking for updates")
	}()
}
