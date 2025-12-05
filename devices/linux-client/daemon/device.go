package daemon

import (
	"bytes"
	"context"
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
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	log "github.com/sirupsen/logrus"

	"github.com/antmicro/rdfm/devices/linux-client/actions"
	"github.com/antmicro/rdfm/devices/linux-client/app"
	"github.com/antmicro/rdfm/devices/linux-client/conf"
	"github.com/antmicro/rdfm/devices/linux-client/serverws"
	"github.com/antmicro/rdfm/devices/linux-client/shell"
	"github.com/antmicro/rdfm/devices/linux-client/telemetry"

	netUtils "github.com/antmicro/rdfm/devices/linux-client/daemon/net_utils"
)

const RSA_DEVICE_KEY_SIZE = 4096
const TOKEN_EXPIRY_MIN_ALLOWED = 5

type Device struct {
	name                string
	fileMetadata        string
	metadata            map[string]interface{}
	macAddr             string
	rdfmCtx             *app.RDFM
	deviceToken         string
	deviceTokenAcquired int64
	tokenMutex          sync.Mutex
	httpTransport       *http.Transport
	logManager          *telemetry.LogManager
	conn                *serverws.DeviceManagementConnection
	actionRunner        *actions.ActionRunner
	shellRunner         *shell.ShellRunner
	kafkaRunner         *telemetry.KafkaRunner
	triggerUpdateCheck  chan bool
}

func (d *Device) isFsAccessAllowed(file string) bool {
	baseDir, err := filepath.EvalSymlinks(d.rdfmCtx.RdfmConfig.FileSystemBaseDir)
	if err != nil {
		return false
	}
	file, err = filepath.EvalSymlinks(file)
	if err != nil {
		return false
	}
	relPath, err := filepath.Rel(baseDir, file)
	if err != nil {
		return false
	}

	return !strings.Contains(relPath, "..")
}

func (d *Device) handleRequest(msg []byte) (serverws.Request, error) {
	var msgMap map[string]interface{}

	err := json.Unmarshal(msg, &msgMap)
	if err != nil {
		log.Errorln("Dropping request. Failed to deserialize:", err)
		return nil, err
	}
	requestName := msgMap["method"]

	log.Infof("Handling '%s' request...", requestName)

	request, err := serverws.Parse(string(msg[:]))
	if err != nil {
		return nil, err
	}

	switch r := request.(type) {
	case serverws.Alert:
		for key, val := range r.Alert {
			log.Printf("Server sent %s: %s", key, val)
		}
	case serverws.ActionExec:
		response := serverws.ActionExecControl{
			Method:      "action_exec_control",
			ExecutionId: r.ExecutionId,
			Status:      "ok",
		}

		ok := d.actionRunner.Execute(r.ExecutionId, r.ActionId)
		if !ok {
			response.Status = "full"
			log.Warnln("Refusing action execution:", r.ExecutionId)
		} else {
			log.Infoln("Accepting action execution:", r.ExecutionId)
		}

		return response, nil
	case serverws.ActionListQuery:
		action_list := d.actionRunner.List()
		var reqActions []serverws.Action
		for _, action := range action_list {
			reqAction := serverws.Action{
				ActionId:    action.GetId(),
				ActionName:  action.GetName(),
				Description: action.GetDescription(),
			}

			switch v := action.(type) {
			case actions.CommandAction:
				reqAction.Command = v.Command
				reqAction.Timeout = v.Timeout
			default:
				reqAction.Command = []string{}
				reqAction.Timeout = 0.0
			}

			reqActions = append(reqActions, reqAction)
		}
		response := serverws.ActionListUpdate{
			Method:  "action_list_update",
			Actions: reqActions,
		}
		return response, nil
	case serverws.DeviceAttachToManager:
		tlsConf, err := d.getTlsConf()
		if err != nil {
			log.Warnln("Failed to get TLS configuration:", err)
			return nil, nil
		}

		go func() {
			token, err := d.getDeviceToken()
			if err != nil {
				log.Warnln("Failed to acquire device token:", err)
				return
			}

			session, err := d.shellRunner.Spawn(r.Uuid, d.rdfmCtx.RdfmConfig.ShellPath)
			if err != nil {
				log.Warnln("Failed to spawn shell session:", err)
				return
			}
			defer d.shellRunner.Terminate(session.Uuid())

			conn := serverws.NewShellConnection(d.rdfmCtx.RdfmConfig.ServerURL, tlsConf)
			err = conn.Connect(token, r.MacAddr, r.Uuid)
			if err != nil {
				log.Warnln("Failed to connect to shell WebSocket:", err)
				return
			}
			defer conn.Close()

			err = session.Run(conn)
			log.Debugf("Shell session %s exited with err: %s", session.Uuid(), err)
		}()

		return nil, nil
	case serverws.FsFileDownload:
		response := serverws.FsFileDownloadReply{
			Method: "fs_file_download_reply",
			Id:     r.Id,
			Status: 1,
		}

		if !d.isFsAccessAllowed(r.File) {
			return response, nil
		}

		f, err := os.Open(r.File)
		if err != nil {
			return response, nil
		}
		defer f.Close()

		buf := make([]byte, r.PartSize)

		for _, url := range r.UploadUrls {
			c, err := f.Read(buf)
			if err != nil {
				return response, nil
			}

			req, err := http.NewRequest(http.MethodPut, url, bytes.NewReader(buf[:c]))
			if err != nil {
				return nil, err
			}
			client := &http.Client{}
			ret, err := client.Do(req)
			if err != nil {
				return nil, err
			} else {
				response.Etags = append(response.Etags, ret.Header.Get("Etag"))
			}
		}

		response.Status = 0

		return response, nil
	case serverws.FsFileProbe:
		response := serverws.FsFileProbeReply{
			Method: "fs_file_probe_reply",
			Id:     r.Id,
			Status: 1,
		}

		if !d.isFsAccessAllowed(r.File) {
			return response, nil
		}

		f, err := os.Open(r.File)
		if err != nil {
			return response, nil
		}
		defer f.Close()
		stat, err := f.Stat()
		if err != nil {
			return response, nil
		}
		response.Size = stat.Size()
		response.Status = 0

		return response, nil
	default:
		log.Warnf("Request '%s' is unsupported", requestName)
		response := serverws.CantHandleRequest()
		return response, nil
	}
	return nil, nil
}

func (d *Device) marshalSendRetry(req serverws.Request, cancelCtx context.Context) error {
	msg, err := json.Marshal(req)
	if err != nil {
		return err
	}

	expBackoff := netUtils.NewExpBackoff(200*time.Millisecond, 10*time.Second, 2)

	for {
		err := d.conn.Send(msg)
		if err == nil {
			break
		}

		log.Warnf("Sending response failed. Retrying in %.3fs.", expBackoff.Peek().Seconds())
		select {
		case <-time.After(expBackoff.Retry()):
		case <-cancelCtx.Done():
			log.Warnln("Dropping response due to cancel.")
			return context.Canceled
		}
	}
	return nil
}

func (d *Device) getTlsConf() (*tls.Config, error) {
	if d.rdfmCtx.RdfmConfig.ServerCertificate == "" {
		log.Fatalf("No server certificate path in %s!", conf.RdfmOverlayConfigPath)
	}
	cert, err := os.ReadFile(d.rdfmCtx.RdfmConfig.ServerCertificate)
	if err != nil {
		log.Fatal("Failed to read certificate file: ",
			d.rdfmCtx.RdfmConfig.ServerCertificate, err)
		return nil, err
	}
	os.Setenv("SSL_CERT_DIR",
		filepath.Dir(string(d.rdfmCtx.RdfmConfig.ServerCertificate)))
	log.Infof("Set $SSL_CERT_DIR to \"%s\"\n",
		os.Getenv("SSL_CERT_DIR"))
	caCertPool := x509.NewCertPool()
	caCertPool.AppendCertsFromPEM(cert)
	if len(cert) < 1 {
		return nil, errors.New("certificate empty")
	}
	return &tls.Config{
		RootCAs: caCertPool,
	}, nil
}

func (d *Device) prepareHttpTransport(tlsConf *tls.Config) *http.Transport {
	if tlsConf != nil {
		return &http.Transport{TLSClientConfig: tlsConf}
	} else {
		return &http.Transport{}
	}
}

func (d *Device) setupConnection() error {
	// Get MAC address
	mac, err := netUtils.GetUniqueId()
	if err != nil {
		return err
	}
	d.macAddr = *mac

	// Check whether we should encrypt connection
	serverUrl := d.rdfmCtx.RdfmConfig.ServerURL
	if serverUrl == "" {
		log.Fatalf("No server URL in %s!", conf.RdfmOverlayConfigPath)
	}
	shouldEncrypt, err := netUtils.ShouldEncryptProxy(serverUrl)
	if err != nil {
		return err
	}

	var tlsConf *tls.Config = nil
	if shouldEncrypt {
		tlsConf, err = d.getTlsConf()
		if err != nil {
			return err
		}
	}

	d.httpTransport = d.prepareHttpTransport(tlsConf)
	d.conn = serverws.NewDeviceConnection(serverUrl, tlsConf, 1024)
	d.conn.SetCapability("action", d.rdfmCtx.RdfmConfig.ActionEnable)
	d.conn.SetCapability("shell", d.rdfmCtx.RdfmConfig.ShellEnable)
	d.conn.SetCapability("filesystem", d.rdfmCtx.RdfmConfig.FileSystemEnable)
	d.conn.SetCapability("update-progress", d.rdfmCtx.RdfmConfig.UpdateProgressEnable)
	return nil
}

func (d *Device) setupActionRunner() error {
	actionRunner, err := actions.NewActionRunner(d.rdfmCtx, d.rdfmCtx.RdfmConfig.ActionQueueSize, d.actionResultCallback, conf.RdfmActionDataPath)
	if err != nil {
		return err
	}
	d.actionRunner = actionRunner
	return nil
}

func (d *Device) setupShellRunner() error {
	sr, err := shell.NewShellRunner(d.rdfmCtx.RdfmConfig.ShellConcurrentMaxCount)
	if err != nil {
		return err
	}
	d.shellRunner = sr
	return nil
}

func (d *Device) setupKafkaRunner() error {
	tlsConf, err := d.getTlsConf()
	if err != nil {
		return err
	}

	tokenCb := func() (string, error) {
		return d.getDeviceToken()
	}

	kr := telemetry.NewKafkaRunner(
		d.macAddr,
		tlsConf,
		d.rdfmCtx.RdfmConfig.TelemetryBootstrapServers,
		d.rdfmCtx.RdfmConfig.TelemetryBatchSize,
		tokenCb,
	)
	d.kafkaRunner = kr
	return nil
}

func (d *Device) actionResultCallback(result actions.ActionResult, cancelCtx context.Context) bool {
	res := serverws.ActionExecResult{
		Method:      "action_exec_result",
		ExecutionId: result.ExecId,
		StatusCode:  result.StatusCode,
		Output:      *result.Output,
	}

	err := d.marshalSendRetry(res, cancelCtx)
	if err != nil {
		log.Warnln("Sending action result failed:", err)
		return false
	}
	return true
}

func (d *Device) maintainDeviceConnection(cancelCtx context.Context) {
	expBackoff := netUtils.NewExpBackoff(200*time.Millisecond, 5*time.Second, 2)
	expBackoffResetThreshold := 10 * time.Second
	for {
		select {
		case <-time.After(expBackoff.Retry()):
		case <-cancelCtx.Done():
			return
		}

		deviceToken, err := d.getDeviceToken()
		if err != nil {
			log.Warnln("Restarting device connection. Couldn't obtain device token:", err)
			continue
		}

		startTime := time.Now()
		err = d.conn.CreateConnection(deviceToken, cancelCtx)
		if err != nil {
			log.Warnln("Restarting device connection due to:", err)
		}
		if time.Since(startTime) > expBackoffResetThreshold {
			expBackoff.Reset()
		}
	}
}

func (d *Device) communicationLoop(cancelCtx context.Context) error {
	quitCh := make(chan bool, 1)
	defer close(quitCh)

	go func() {
		select {
		case <-cancelCtx.Done():
		case <-quitCh:
		}
	}()

	for {
		select {
		case <-cancelCtx.Done():
			return nil
		default:
		}

		msg := d.conn.Recv(cancelCtx)
		if msg == nil {
			continue
		}

		res, err := d.handleRequest(msg)
		if err != nil {
			return err
		}
		if res != nil {
			err := d.marshalSendRetry(res, cancelCtx)
			if err != nil {
				return err
			}
		}
	}
}

func (d *Device) managementWsLoop(cancelCtx context.Context) {
	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer func() {
			log.Infoln("Device connection finished.")
			wg.Done()
		}()
		log.Infoln("Starting device connection...")
		d.maintainDeviceConnection(cancelCtx)
	}()

	wg.Add(1)
	go func() {
		defer func() {
			log.Infoln("Action runner finished.")
			wg.Done()
		}()
		log.Infoln("Starting action runner...")
		d.actionRunner.StartWorker(cancelCtx)
	}()

	wg.Add(1)
	go func() {
		defer func() {
			log.Infoln("Communication loop finished.")
			wg.Done()
		}()
		log.Infoln("Starting communication loop...")
		if err := d.communicationLoop(cancelCtx); err != nil {
			panic(err)
		}
	}()

	wg.Wait()
}

func (d *Device) getDeviceToken() (string, error) {
	d.tokenMutex.Lock()
	defer d.tokenMutex.Unlock()

	payload, err := netUtils.ExtractJwtPayload(d.deviceToken)
	if err == nil {
		// check if reauth needed in the next TOKEN_EXPIRY_MIN_ALLOWED or less seconds
		if d.deviceTokenAcquired+payload.Expires-TOKEN_EXPIRY_MIN_ALLOWED <= time.Now().Unix() {
			err = d.authenticateDeviceWithServer()
			if err != nil {
				return "", err
			}
		}
	} else {
		// extraction failed
		log.Warnln("Device token missing or malformed, authenticating...")
		err := d.authenticateDeviceWithServer()
		if err != nil {
			return "", err
		}
	}

	// d.authenticateDeviceWithServer should have taken care of fetching the token if necessary
	return d.deviceToken, nil
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
	keyFileName := conf.RdfmRSAKeysPath

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

	metadata, err := d.collectMetadata()
	if err != nil {
		return err
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
			d.deviceTokenAcquired = time.Now().Unix()
			return nil
		case 400:
			log.Println("Invalid message schema or signature")
		case 401:
			authDuration := time.Duration(d.rdfmCtx.RdfmConfig.RetryPollIntervalSeconds) * time.Second
			log.Println("Device hasn't been authorized by the administrator.")
			log.Println("Next authorization attempt in", authDuration)
			time.Sleep(time.Duration(authDuration))
		default:
			log.Println("Unexpected status code from the server:", res.StatusCode)
		}
	}
}

// collectMetadata gathers the RDFM metadata for this device.
func (d *Device) collectMetadata() (map[string]interface{}, error) {
	metadata, err := conf.LoadMetadataFile(d.rdfmCtx.RdfmConfig.MetadataFilePath)
	if err != nil {
		log.Warnln("Error collecting metadata: failed to get base metadata file:", err)
	}

	// make sure we have a MAC
	if d.macAddr == "" {
		mac, err := netUtils.GetUniqueId()
		if err != nil {
			return nil, fmt.Errorf("Error collecting metadata: failed to get MAC address: %w", err)
		}
		d.macAddr = *mac
	}

	devType, err := d.rdfmCtx.GetCurrentDeviceType()
	if err != nil {
		return nil, fmt.Errorf("Error collecting metadata: failed to get current device type: %w", err)
	}

	swVer, err := d.rdfmCtx.GetCurrentArtifactName()
	if err != nil {
		return nil, fmt.Errorf("Error collecting metadata: failed to get current software version: %w", err)
	}

	tags, err := conf.LoadTagsConfig(conf.RdfmDefaultTagsPath)
	if err != nil {
		return nil, fmt.Errorf("Error collecting metadata: failed to get current tags: %w", err)
	}

	m := map[string]interface{}{
		"rdfm.hardware.devtype":         devType,
		"rdfm.software.version":         swVer,
		"rdfm.hardware.macaddr":         d.macAddr,
		"rdfm.software.supports_rsync":  "true",
		"rdfm.software.supports_xdelta": "true",
		"rdfm.software.tags":            tags,
	}
	if len(tags) == 0 {
		delete(m, "rdfm.software.tags")
	}
	for k, v := range m {
		metadata[k] = v
	}
	return metadata, nil
}

func (d *Device) requestUpdateCheck() {
	d.triggerUpdateCheck <- true
}
