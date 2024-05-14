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

type IdConfig struct {
	Name string
	Id   string
}

type DeviceConfig struct {
	IdConfig `mapstructure:",squash"`

	DevType        string `mapstructure:"dev_type"`
	Key            string
	UpdateInterval *time.Duration `mapstructure:"update_interval,omitempty"`
	SelfConfirm    bool           `mapstructure:"self_confirm,omitempty"`
	Transport      TransportConfig
}

type GroupMemberConfig struct {
	Name        string
	Device      string
	SelfConfirm bool `mapstructure:"self_confirm,omitempty"`

	Transport TransportConfig
}

type GroupConfig struct {
	IdConfig `mapstructure:",squash"`

	Type           string
	Key            string
	UpdateInterval *time.Duration `mapstructure:"update_interval,omitempty"`

	Members []GroupMemberConfig
}

type AppConfig struct {
	Server         string
	KeyDir         string `mapstructure:"key_dir"`
	Retries        uint
	UpdateInterval *time.Duration `mapstructure:"update_interval"`

	Devices []DeviceConfig

	Groups []GroupConfig

	logVerbose bool
}
