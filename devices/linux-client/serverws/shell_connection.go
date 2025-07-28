package serverws

import (
	"crypto/tls"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"

	"github.com/creack/pty"
	"github.com/gorilla/websocket"
	log "github.com/sirupsen/logrus"
	"golang.org/x/sync/errgroup"
)

const (
	ShellCopyBufferSize = 16384
)

// Represents a bidirectional device shell WebSocket connection.
type ShellConnection struct {
	serverUrl string
	dialer    *websocket.Dialer
	ws        *websocket.Conn
}

// Prepare a reverse shell connection with the server. To actually connect to
// the session, call Connect with the token, device identifier and shell session
// ID.
func NewShellConnection(serverUrl string, tlsConf *tls.Config) *ShellConnection {
	sc := new(ShellConnection)
	sc.serverUrl = serverUrl
	sc.dialer = prepareWsDialer(serverUrl, tlsConf)
	return sc
}

// Connect to the RDFM WebSocket associated with the specified shell session.
func (sc *ShellConnection) Connect(deviceToken string, macAddr string, shellUuid string) error {
	endpoint, err := formatShellWsUrl(sc.serverUrl, macAddr, shellUuid)
	if err != nil {
		return err
	}
	sc.ws, err = ConnectToRdfmWs(*sc.dialer, endpoint, deviceToken)
	if err != nil {
		return err
	}
	return nil
}

// Copy data bidirectionally between the specified open PTY and the connected
// WebSocket. Blocks until either the PTY or the WebSocket are closed.
func (sc *ShellConnection) Copy(pts *os.File, command *exec.Cmd) error {
	var g errgroup.Group
	// WS -> Shell
	g.Go(func() error {
		for {
			t, b, err := sc.ws.ReadMessage()
			if err != nil {
				log.Debugf("WS read returned err: %s", err)
				return err
			}
			if t != websocket.BinaryMessage {
				// NOTE: Shell data is transferred using binary messages
				// exclusively, as it can contain control characters. Text
				// messages are used for control messages (e.g terminal resize).
				message := string(b[:])
				parts := strings.Split(message, " ")
				if parts == nil {
					continue
				}
				if parts[0] == "resize" {
					rows, _ := strconv.Atoi(parts[1])
					cols, _ := strconv.Atoi(parts[2])
					pty.Setsize(pts, &pty.Winsize{
						Rows: uint16(rows),
						Cols: uint16(cols),
					})
					command.Process.Signal(syscall.SIGWINCH)
				}
				continue
			}
			_, err = pts.Write(b)
			if err != nil {
				log.Debugf("FD write returned err: %s", err)
				return err
			}
		}
	})
	// Shell -> WS
	g.Go(func() error {
		b := make([]byte, ShellCopyBufferSize)
		for {
			n, err := pts.Read(b)
			if err != nil {
				log.Debugf("PTY read returned err: %s", err)
				return err
			}
			err = sc.ws.WriteMessage(websocket.BinaryMessage, b[:n])
			if err != nil {
				log.Debugf("WS write returned err: %s", err)
				return err
			}
		}
	})
	return g.Wait()
}

// Close the WebSocket connection.
func (sc *ShellConnection) Close() error {
	return sc.ws.Close()
}
