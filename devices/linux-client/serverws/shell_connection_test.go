package serverws

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	log "github.com/sirupsen/logrus"
	"github.com/stretchr/testify/assert"
)

var (
	TestData = []byte{0x40, 0x40, 0x40, 0x40}
)

const (
	TestDefaultTimeout = 5 * time.Second
	// Values are irrelevant.
	MockToken   = "TOKEN"
	MockMacAddr = "MACADDR"
	MockUuid    = "UUID"
)

type MockWebsocketServer struct {
	server   *httptest.Server
	upgrader websocket.Upgrader
	received chan []byte
	toSend   chan []byte
}

func NewMockWebsocketServer(isTls bool) *MockWebsocketServer {
	s := new(MockWebsocketServer)
	s.received = make(chan []byte)
	s.toSend = make(chan []byte)
	s.upgrader = websocket.Upgrader{}
	if isTls {
		s.server = httptest.NewTLSServer(s)
	} else {
		s.server = httptest.NewServer(s)
	}
	return s
}

func (s *MockWebsocketServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.upgrader.CheckOrigin = func(r *http.Request) bool { return true }
	ws, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer ws.Close()

	go func() {
		for {
			m := <-s.toSend
			log.Infoln("Sending binary message:", m)
			err = ws.WriteMessage(websocket.BinaryMessage, m)
			if err != nil {
				return
			}
		}
	}()
	for {
		_, m, err := ws.ReadMessage()
		if err != nil {
			return
		}
		log.Infoln("Received binary message:", m)
		s.received <- m
	}
}

func TestShellConnectionNoTLS(t *testing.T) {
	ws := NewMockWebsocketServer(false)
	conn := NewShellConnection(ws.server.URL, nil)
	err := conn.Connect(MockToken, MockMacAddr, MockUuid)
	assert.Nil(t, err)
}

func TestShellConnectionRead(t *testing.T) {
	mwss := NewMockWebsocketServer(false)
	conn := NewShellConnection(mwss.server.URL, nil)

	err := conn.Connect(MockToken, MockMacAddr, MockUuid)
	assert.Nil(t, err)

	// Create pipe to simulate tty. Pass the *read* end of the pipe as we want
	// to test reads.
	r, w, err := os.Pipe()
	go conn.Copy(r)
	// Write test data to the write pipe, it should be received over the mock
	// websocket.
	_, err = w.Write(TestData)
	assert.NoError(t, err)

	ctx, _ := context.WithTimeout(context.Background(), TestDefaultTimeout)
	select {
	case <-ctx.Done():
		{
			assert.Fail(t, "Timed out waiting for WebSocket message contents")
		}
	case v := <-mwss.received:
		{
			assert.Equal(t, v, TestData)
		}
	}
}

func TestShellConnectionWrite(t *testing.T) {
	ws := NewMockWebsocketServer(false)
	conn := NewShellConnection(ws.server.URL, nil)

	err := conn.Connect(MockToken, MockMacAddr, MockUuid)
	assert.Nil(t, err)

	// Create pipe to simulate tty. Pass the *write* end of the pipe as we want
	// to test writes.
	r, w, err := os.Pipe()
	go conn.Copy(w)
	// Send data over the mock websocket, it should be readable on the read end
	// of the pipe.
	ws.toSend <- TestData

	b := make([]byte, len(TestData))
	r.SetDeadline(time.Now().Add(TestDefaultTimeout))
	_, err = r.Read(b)
	if assert.NoError(t, err) {
		assert.Equal(t, b, TestData)
	}
}
