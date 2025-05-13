package serverws

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"sync"

	"github.com/gorilla/websocket"
	log "github.com/sirupsen/logrus"
)

type deviceConnectionState int

const (
	stateDisconnected deviceConnectionState = iota
	stateConnected
)

type DeviceManagementConnection struct {
	ws           *websocket.Conn
	rx           chan []byte
	txMut        sync.Mutex
	wsMut        sync.RWMutex
	serverUrl    string
	dialer       websocket.Dialer
	stateCnd     *sync.Cond
	state        deviceConnectionState
	capabilities map[string]bool
}

type ConnClosedError struct {
	message string
}

func (e *ConnClosedError) Error() string {
	return e.message
}

func (d *DeviceManagementConnection) startRecvLoop(cancelCtx context.Context) error {
	for {
		d.wsMut.RLock()
		if d.ws == nil {
			return &ConnClosedError{"connection is closed"}
		}
		_, msg, err := d.ws.ReadMessage()
		d.wsMut.RUnlock()
		if err != nil {
			return err
		}
		select {
		case d.rx <- msg:
		case <-cancelCtx.Done():
			return nil
		}
	}
}

func (d *DeviceManagementConnection) Close() error {
	d.stateCnd.L.Lock()
	defer d.stateCnd.L.Unlock()
	err := d.tryClose()
	for d.state != stateDisconnected {
		d.stateCnd.Wait()
	}
	return err
}

func (d *DeviceManagementConnection) tryClose() error {
	d.wsMut.RLock()
	defer d.wsMut.RUnlock()
	if d.ws != nil {
		return d.ws.Close()
	}
	return nil
}

func (d *DeviceManagementConnection) setState(state deviceConnectionState) {
	d.stateCnd.L.Lock()
	d.state = state
	d.stateCnd.Broadcast()
	d.stateCnd.L.Unlock()
}

func (d *DeviceManagementConnection) announceCapabilities() error {
	res := map[string]interface{}{
		"method":       "capability_report",
		"capabilities": d.capabilities,
	}

	msg, err := json.Marshal(res)
	if err != nil {
		return err
	}

	d.Send(msg)
	return nil
}

func (d *DeviceManagementConnection) CreateConnection(deviceToken string, cancelCtx context.Context) error {
	var wg sync.WaitGroup

	defer func() {
		d.tryClose()
		d.setState(stateDisconnected)
	}()

	endpoint, err := formatDeviceWsUrl(d.serverUrl)
	if err != nil {
		return err
	}
	d.ws, err = ConnectToRdfmWs(d.dialer, endpoint, deviceToken)
	if err != nil {
		return err
	}

	quitCh := make(chan bool, 1)
	defer close(quitCh)

	go func() {
		select {
		case <-cancelCtx.Done():
			d.tryClose()
		case <-quitCh:
		}
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Infoln("Starting recv loop...")
		err = d.startRecvLoop(cancelCtx)
		if err != nil {
			log.Errorln("Closing connection. Receiver error:", err)
			d.tryClose()
		}
	}()

	wg.Add(1)
	go func() {
		var err error
		defer wg.Done()
		log.Infoln("Starting greeter...")
		err = d.announceCapabilities()
		if err != nil {
			log.Errorln("Closing connection. Greeter error:", err)
			d.tryClose()
		} else {
			log.Infoln("Greeter finished.")
			d.setState(stateConnected)
		}
	}()

	log.Infoln("Starting connection...")
	wg.Wait()
	log.Infoln("Connection closed.")

	return err
}

func NewDeviceConnection(serverUrl string, tlsConf *tls.Config, buffer_size int) *DeviceManagementConnection {
	dc := new(DeviceManagementConnection)
	dc.rx = make(chan []byte, buffer_size)
	dc.serverUrl = serverUrl
	dc.dialer = *prepareWsDialer(serverUrl, tlsConf)
	dc.state = stateDisconnected
	dc.stateCnd = sync.NewCond(&sync.Mutex{})
	dc.capabilities = make(map[string]bool)
	return dc
}

func (d *DeviceManagementConnection) Recv(cancelCtx context.Context) []byte {
	select {
	case msg, ok := <-d.rx:
		if ok {
			return msg
		}
	case <-cancelCtx.Done():
	}
	return nil
}

func (d *DeviceManagementConnection) Send(msg []byte) error {
	d.txMut.Lock()
	d.wsMut.RLock()
	defer d.txMut.Unlock()
	defer d.wsMut.RUnlock()
	if d.ws == nil {
		return &ConnClosedError{"connection is closed"}
	}
	err := d.ws.WriteMessage(websocket.TextMessage, msg)

	if err != nil {
		log.Println("Sender error:", err)
		return err
	}
	return nil
}

func (d *DeviceManagementConnection) EnsureReady() {
	d.stateCnd.L.Lock()
	defer d.stateCnd.L.Unlock()
	for d.state != stateConnected {
		d.stateCnd.Wait()
	}
}

func (d *DeviceManagementConnection) SetCapability(cap string, value bool) {
	d.capabilities[cap] = value
}
