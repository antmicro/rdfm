package serverws

import (
	"crypto/tls"
	"fmt"
	"net/http"
	"net/url"

	"github.com/gorilla/websocket"
	log "github.com/sirupsen/logrus"
)

func formatDeviceWsUrl(serverUrl string) (string, error) {
	return url.JoinPath(serverUrl, "/api/v1/devices/ws")
}

func formatShellWsUrl(serverUrl string, macAddr string, shellUuid string) (string, error) {
	return url.JoinPath(serverUrl,
		fmt.Sprintf("/api/v1/devices/%s/shell/attach/%s", macAddr, shellUuid))
}

func prepareWsDialer(serverUrl string, tlsConf *tls.Config) *websocket.Dialer {
	url, err := url.Parse(serverUrl)
	if err != nil {
		return websocket.DefaultDialer
	}
	switch url.Scheme {
	default:
		fallthrough
	case "http":
		{
			return websocket.DefaultDialer
		}
	case "https":
		{
			return &websocket.Dialer{TLSClientConfig: tlsConf}
		}
	}
}

func ConnectToRdfmWs(dialer websocket.Dialer, endpoint string, deviceToken string) (*websocket.Conn, error) {
	scheme := "ws"
	if dialer.TLSClientConfig != nil {
		scheme = "wss"
	}
	url, err := url.Parse(endpoint)
	if err != nil {
		return nil, err
	}
	url.Scheme = scheme
	wsEndpoint := url.String()

	log.Infoln("Connecting to", wsEndpoint)
	authHeader := http.Header{
		"Authorization": []string{"Bearer token=" + deviceToken},
	}
	ws, _, err := dialer.Dial(wsEndpoint, authHeader)
	return ws, err
}
