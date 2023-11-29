package daemon

import (
	"bytes"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"time"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	"github.com/antmicro/rdfm/daemon/proxy"
	"github.com/gorilla/websocket"

	netUtils "github.com/antmicro/rdfm/daemon/net_utils"
	packages "github.com/antmicro/rdfm/daemon/packages"
	requests "github.com/antmicro/rdfm/daemon/requests"
)

const MSG_RECV_TIMEOUT_INTERVALS = 10
const MSG_RECV_INTERVAL_S = 1
const RSA_DEVICE_KEY_SIZE = 4096

type AuthToken struct {
	value string
	// Path to file where auth token is saved
	file string
}

type Device struct {
	name         string
	fileMetadata string
	encryptProxy bool
	ws           *websocket.Conn
	metadata     map[string]interface{}
	caps         capabilities.DeviceCapabilities
	macAddr      string
	rdfmCtx      *app.RDFM
	authToken    *AuthToken
	deviceToken  string
}

func (d Device) recv() (requests.Request, error) {
	var msg []byte
	var err error

	for i := 0; i < MSG_RECV_TIMEOUT_INTERVALS; i++ {
		_, msg, err = d.ws.ReadMessage()
		if err != nil {
			return nil, err
		}
		if len(msg) > 0 {
			break
		}
		time.Sleep(MSG_RECV_INTERVAL_S * time.Second)
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
	err = d.ws.WriteMessage(websocket.TextMessage, []byte(s_msg))
	if err != nil {
		log.Println(err)
		return err
	}
	return nil
}

func (d *Device) startClient() error {
	d.checkUpdatesPeriodically()
	err := d.communicationLoop()
	defer d.ws.Close()
	if err != nil {
		log.Println("Error running client", err)
		return err
	}
	return nil
}

func (d *Device) connect() error {
	var dialer websocket.Dialer
	var scheme string

	// Get MAC address
	mac, err := netUtils.GetMacAddr()
	if err != nil {
		return err
	}
	d.macAddr = mac

	// Get device token
	d.authenticateDeviceWithServer()

	authHeader := http.Header{
		"Authorization": []string{"Bearer token=" + d.deviceToken},
	}

	if d.encryptProxy {
		cert, err := os.ReadFile(d.rdfmCtx.RdfmConfig.ServerCertificate)
		if err != nil {
			log.Fatal("Failed to read certificate file: ",
				d.rdfmCtx.RdfmConfig.ServerCertificate, err)
			return err
		}
		conf := &tls.Config{}
		os.Setenv("SSL_CERT_DIR",
			filepath.Dir(string(d.rdfmCtx.RdfmConfig.ServerCertificate)))
		log.Printf("Set $SSL_CERT_DIR to \"%s\"\n",
			os.Getenv("SSL_CERT_DIR"))
		caCertPool := x509.NewCertPool()
		caCertPool.AppendCertsFromPEM(cert)
		conf = &tls.Config{
			RootCAs: caCertPool,
		}
		if len(cert) < 1 {
			return errors.New("Certificate empty")
		}
		scheme = "wss"
		dialer = websocket.Dialer{
			TLSClientConfig: conf,
		}
		log.Println("Creating WebSocket over TLS")
	} else {
		scheme = "ws"
		dialer = *websocket.DefaultDialer
		log.Println("Creating WebSocket")
	}

	// Open a WebSocket connection
	var needPort = true
	serverUrl := d.rdfmCtx.RdfmConfig.ServerURL
	addr, err := netUtils.AddrWithOrWithoutPort(serverUrl, needPort)
	if err != nil {
		return err
	}
	u := url.URL{Scheme: scheme, Host: addr, Path: "/api/v1/devices/ws"}
	log.Println("Connecting to", u.String())

	d.ws, _, err = dialer.Dial(u.String(), authHeader)
	if err != nil {
		log.Println("Failed to create WebSocket", err)
		return err
	}
	log.Println("WebSocket created")

	return nil
}

func (d *Device) communicationLoop() error {
	for {
		req, err := d.recv()
		if err != nil {
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
		var needPort = false
		addr, err := netUtils.AddrWithOrWithoutPort(d.ws.LocalAddr().String(), needPort)
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
	case requests.Alert:
		for key, val := range r.Alert {
			log.Printf("Server sent %s: %s", key, val)
		}
	default:
		log.Printf("Unsupported request: %s", r)
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

func getPublicKey(privateKey *rsa.PrivateKey) []byte {
	publicKey := privateKey.PublicKey
	publicKeyBytes := x509.MarshalPKCS1PublicKey(&publicKey)
	publicKeyBlock := pem.Block{
		Type:    "PUBLIC KEY",
		Headers: nil,
		Bytes:   publicKeyBytes,
	}
	return pem.EncodeToMemory(&publicKeyBlock)
}

func (d Device) getKeys() (*rsa.PrivateKey, string) {
	var publicKeyPem []byte
	var privateKey *rsa.PrivateKey
	keyFileName := app.RdfmRSAKeysPath

	// Read key from file
	privateKeyPem, err := os.ReadFile(keyFileName)
	if err != nil || len(privateKeyPem) == 0 {
		log.Println("Can't read keys from the file")
		log.Println("Generating keys...")

		// Generate the keys
		privateKey, err = rsa.GenerateKey(rand.Reader, RSA_DEVICE_KEY_SIZE)
		if err != nil {
			return nil, ""
		}
		publicKeyPem = getPublicKey(privateKey)
		log.Println("Keys generated")

		// Write keys to a file
		privateKeyBytes := x509.MarshalPKCS1PrivateKey(privateKey)
		privateKeyBlock := pem.Block{
			Type:    "PRIVATE KEY",
			Headers: nil,
			Bytes:   privateKeyBytes,
		}
		privateKeyPem := pem.EncodeToMemory(&privateKeyBlock)
		err = os.WriteFile(keyFileName, privateKeyPem, 0600)
		if err != nil {
			log.Println("Can't write key to the file")
		} else {
			log.Println("Keys written to a file")
		}
	} else {
		// Get private key
		privateKeyBlock, _ := pem.Decode(privateKeyPem)
		if privateKeyBlock == nil || privateKeyBlock.Type != "PRIVATE KEY" {
			log.Println("Failed to decode PEM block containing private key")
		}
		privateKey, err = x509.ParsePKCS1PrivateKey(privateKeyBlock.Bytes)
		if err != nil {
			log.Println("Failed to parse private key bytes")
		}
		// Get public key
		publicKeyPem = getPublicKey(privateKey)
	}
	return privateKey, string(publicKeyPem)
}

func (d *Device) authenticateDeviceWithServer() {

	privateKey, publicKeyString := d.getKeys()
	if len(publicKeyString) == 0 {
		log.Println("Failed to get device key. Authentication impossible")
		return
	}
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

	log.Println("Device authentication...")
	metadata := map[string]string{
		"rdfm.hardware.devtype": devType,
		"rdfm.software.version": swVer,
		"rdfm.hardware.macaddr": d.macAddr,
	}
	msg := map[string]interface{}{
		"metadata":   metadata,
		"public_key": publicKeyString,
		"timestamp":  time.Now().Unix(),
	}
	serializedMsg, err := json.Marshal(msg)
	if err != nil {
		log.Println("Failed to serialize metadata", err)
		return
	}

	// Prepare signature
	hash := sha256.Sum256(serializedMsg)
	signature, err := rsa.SignPKCS1v15(rand.Reader, privateKey, crypto.SHA256, hash[:])
	if err != nil {
		log.Println("Failed to sign auth request", err)
		return
	}
	signatureB64 := base64.StdEncoding.EncodeToString([]byte(signature))

	endpoint := fmt.Sprintf("%s/api/v1/auth/device",
		d.rdfmCtx.RdfmConfig.ServerURL)
auth_loop:
	for {
		req, _ := http.NewRequest("POST", endpoint, bytes.NewBuffer(serializedMsg))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Add("Accept", "application/json, text/javascript")
		req.Header.Add("X-RDFM-Device-Signature", signatureB64)
		client := &http.Client{}
		res, err := client.Do(req)

		if err != nil {
			log.Println("Failed to send authentication request", err)
			return
		}
		defer res.Body.Close()

		switch res.StatusCode {
		case 200:
			log.Println("Device authorized")
			var response map[string]interface{}
			body, err := io.ReadAll(res.Body)
			err = json.Unmarshal(body, &response)
			if err != nil {
				log.Println("Failed to deserialize package metadata", err)
				return
			}
			d.deviceToken = response["token"].(string)
			log.Println("Authorization token expires in", response["expires"], "seconds")
			break auth_loop
		case 400:
			log.Println("Invalid message schema or signature")
		case 401:
			auth_duration := time.Duration(d.rdfmCtx.RdfmConfig.RetryPollIntervalSeconds) * time.Second
			log.Println("Device hasn't been authorized by the administrator.")
			log.Println("Next authorization attempt in", auth_duration)
			time.Sleep(time.Duration(auth_duration))
		default:
			log.Println("Unexpected status code from the server:", res.StatusCode)
		}
	}
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
			if len(d.deviceToken) == 0 {
				d.authenticateDeviceWithServer()
			}

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
			req, _ := http.NewRequest("POST", endpoint,
				bytes.NewBuffer(serializedMetadata),
			)
			req.Header.Set("Content-Type", "application/json")
			req.Header.Add("Authorization", "Bearer token="+d.deviceToken)
			client := &http.Client{}
			res, err := client.Do(req)
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
				d.authenticateDeviceWithServer()
				continue
			}
			update_duration := time.Duration(d.rdfmCtx.RdfmConfig.UpdatePollIntervalSeconds) * time.Second
			log.Printf("Next update check in %s\n", update_duration)
			time.Sleep(time.Duration(update_duration))
		}
		log.Println("Stopped checking for updates")
	}()
}
