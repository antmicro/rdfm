package appcfg

import (
	"time"
)

type BLEConfig struct {
	DeviceIdx int    `mapstructure:"device_index"`
	PeerName  string `mapstructure:"peer_name"`
}

type SerialConfig struct {
	Device string
	Baud   int
	Mtu    int
}

type UDPConfig struct {
	Address string
}

type TransportConfig struct {
	Type string

	BLEConfig    `mapstructure:",squash"`
	SerialConfig `mapstructure:",squash"`
	UDPConfig    `mapstructure:",squash"`
}

type DeviceConfig struct {
	Name           string
	Id             string
	DevType        string         `mapstructure:"dev_type"`
	UpdateInterval *time.Duration `mapstructure:"update_interval,omitempty"`
	Key            string
	Transport      TransportConfig
}

type AppConfig struct {
	Server         string
	KeyDir         string `mapstructure:"key_dir"`
	Retries        uint
	UpdateInterval *time.Duration `mapstructure:"update_interval"`

	Devices []DeviceConfig

	logVerbose bool
}
