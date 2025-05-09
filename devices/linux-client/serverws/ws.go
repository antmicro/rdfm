package serverws

import (
	"crypto/tls"
	"net/http"
	"net/url"

	"github.com/gorilla/websocket"
	log "github.com/sirupsen/logrus"
)

func formatDeviceWsUrl(serverUrl string) (string, error) {
	return url.JoinPath(serverUrl, "/api/v1/devices/ws")
}

func prepareWsDialer(tlsConf *tls.Config) *websocket.Dialer {
	if tlsConf != nil {
		return &websocket.Dialer{TLSClientConfig: tlsConf}
	} else {
		return websocket.DefaultDialer
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
