package transport

import (
	"errors"
	"fmt"
	"rdfm-mcumgr-client/appcfg"
	"strings"
)

// Main abstraction over supported smp protocol transport types
// Used for starting a communication session between app and device
type Transport interface {
	Id() string
	AcqSession() (Session, error)
	Stop() error
}

func InitTransport(cfg appcfg.TransportConfig) (Transport, error) {
	switch strings.ToLower(cfg.Type) {
	case "serial":
		return InitSerialTransport(cfg.SerialConfig)

	case "ble":
		return InitBLETransport(cfg.BLEConfig)

	case "udp":
		return InitUDPTransport(cfg.UDPConfig)

	default:
		return nil, errors.New(fmt.Sprintf("Unknown transport type: %s", cfg.Type))
	}
}
