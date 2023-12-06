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
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"time"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon/capabilities"
	"github.com/gorilla/websocket"

	netUtils "github.com/antmicro/rdfm/daemon/net_utils"
	requests "github.com/antmicro/rdfm/daemon/requests"
)

const MSG_RECV_TIMEOUT_INTERVALS = 10
const MSG_RECV_INTERVAL_S = 1
const RSA_DEVICE_KEY_SIZE = 4096

type Device struct {
	name          string
	fileMetadata  string
	ws            *websocket.Conn
	metadata      map[string]interface{}
	caps          capabilities.DeviceCapabilities
	macAddr       string
	rdfmCtx       *app.RDFM
	deviceToken   string
	httpTransport *http.Transport
}

func (d Device) recv() ([]byte, error) {
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
	return msg, nil
}

func (d Device) send(req requests.Request) error {
	msg, err := json.Marshal(req)
	if err != nil {
		log.Println(err)
		return err
	}
	err = d.ws.WriteMessage(websocket.TextMessage, []byte(msg))
	if err != nil {
		log.Println(err)
		return err
	}
	return nil
}

func (d *Device) handleRequest(msg []byte) (requests.Request, error) {
	var msgMap map[string]interface{}

	err := json.Unmarshal(msg, &msgMap)
	if err != nil {
		log.Println("Failed to deserialize request", err)
		return nil, err
	}
	requestName := msgMap["method"]

	log.Printf("Handling '%s' request...\n", requestName)

	request, err := requests.Parse(string(msg[:]))
	if err != nil {
		return nil, err
	}

	switch r := request.(type) {
	case requests.Alert:
		for key, val := range r.Alert {
			log.Printf("Server sent %s: %s", key, val)
		}
	//case requests.DeviceAttachToManager:
	// TODO: Handle shell_attach
	default:
		log.Printf("Request '%s' is unsupported", requestName)
		response := requests.CantHandleRequest()
		return response, nil
	}
	return nil, nil
}

func (d *Device) communicationCycle() error {
	msg, err := d.recv()
	if err != nil {
		return err
	}
	res, err := d.handleRequest(msg)
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

	// Check whether we should encrypt connection
	serverUrl := d.rdfmCtx.RdfmConfig.ServerURL
	if serverUrl == "" {
		log.Fatalf("No server URL in %s!", app.RdfmOverlayConfigPath)
	}
	encrypt, err := netUtils.ShouldEncryptProxy(serverUrl)
	if err != nil {
		return err
	}

	if encrypt {
		if d.rdfmCtx.RdfmConfig.ServerCertificate == "" {
			log.Fatalf("No server certificate path in %s!", app.RdfmOverlayConfigPath)
		}
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
		if len(cert) < 1 {
			return errors.New("Certificate empty")
		}
		conf = &tls.Config{
			RootCAs: caCertPool,
		}
		d.httpTransport = &http.Transport{TLSClientConfig: conf}
		scheme = "wss"
		dialer = websocket.Dialer{
			TLSClientConfig: conf,
		}
		log.Println("Creating WebSocket over TLS")
	} else {
		d.httpTransport = &http.Transport{}
		scheme = "ws"
		dialer = *websocket.DefaultDialer
		log.Println("Creating WebSocket")
	}

	// Get device token
	err = d.authenticateDeviceWithServer()
	if err != nil {
		return err
	}
	authHeader := http.Header{
		"Authorization": []string{"Bearer token=" + d.deviceToken},
	}

	// Open a WebSocket connection
	var needPort = true
	addr, err := netUtils.HostWithOrWithoutPort(serverUrl, needPort)
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

	// Get a response from the server
	err = d.communicationCycle()
	if err != nil {
		return err
	}

	// Send capabilities
	err = d.send(requests.CapabilityReport{
		Method:       "capability_report",
		Capabilities: d.caps,
	})
	if err != nil {
		log.Println("Failed to send device capabilities to the server")
		return err
	}

	return nil
}

func (d *Device) disconnect() {
	defer d.ws.Close()
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

func (d *Device) authenticateDeviceWithServer() error {
	privateKey, publicKeyString := d.getKeys()
	if len(publicKeyString) == 0 {
		return errors.New("Failed to get device key. Authentication impossible")
	}
	devType, err := d.rdfmCtx.GetCurrentDeviceType()
	if err != nil {
		log.Println("Error getting current device type")
		return err
	}
	swVer, err := d.rdfmCtx.GetCurrentArtifactName()
	if err != nil {
		log.Println("Error getting current software version")
		return err
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
		return err
	}

	// Prepare signature
	hash := sha256.Sum256(serializedMsg)
	signature, err := rsa.SignPKCS1v15(rand.Reader, privateKey, crypto.SHA256, hash[:])
	if err != nil {
		log.Println("Failed to sign auth request", err)
		return err
	}
	signatureB64 := base64.StdEncoding.EncodeToString([]byte(signature))

	endpoint := fmt.Sprintf("%s/api/v1/auth/device",
		d.rdfmCtx.RdfmConfig.ServerURL)

	for {
		req, _ := http.NewRequest("POST", endpoint, bytes.NewBuffer(serializedMsg))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Add("Accept", "application/json, text/javascript")
		req.Header.Add("X-RDFM-Device-Signature", signatureB64)

		var client *http.Client
		client = &http.Client{Transport: d.httpTransport}
		res, err := client.Do(req)

		if err != nil {
			log.Println("Failed to send authentication request", err)
			return err
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
				return err
			}
			d.deviceToken = response["token"].(string)
			log.Println("Authorization token expires in", response["expires"], "seconds")
			if len(d.deviceToken) == 0 {
				return errors.New("Got empty authorization token")
			}
			return nil
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
