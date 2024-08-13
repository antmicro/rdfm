package capabilities

import (
	"encoding/json"

	log "github.com/sirupsen/logrus"

	"github.com/spf13/viper"
)

type DeviceCapabilities struct {
	ShellConnect bool `json:"shell"         mapstructure:"shell"`
}

func LoadCapabilities(path string) (caps DeviceCapabilities, err error) {
	viper.SetConfigFile(path)
	viper.SetDefault("shell", true)

	err = viper.ReadInConfig()
	if err != nil {
		log.Println("Error reading config file", err)
		viper.SafeWriteConfigAs(path)
		log.Println("Generated default capabilities file")
	} else {
		log.Println("Loaded device capabilities")
	}

	capsMap, _ := json.Marshal(viper.AllSettings())
	log.Printf("Device capabilities: %s", capsMap)

	err = viper.Unmarshal(&caps)
	return caps, err
}
