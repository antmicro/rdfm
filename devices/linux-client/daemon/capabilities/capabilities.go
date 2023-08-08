package capabilities

import (
	"log"

	"github.com/spf13/viper"
)

type DeviceCapabilities struct {
	ShellConnect bool `json:"shell_connect" mapstructure:"shell_connect"`
	FileTransfer bool `json:"file_transfer" mapstructure:"file_transfer"`
	ExecCmds     bool `json:"exec_cmds"     mapstructure:"exec_cmds"`
}

func LoadCapabilities(path string) (caps DeviceCapabilities, err error) {
	viper.SetConfigFile(path)
	viper.SetDefault("shell_connect", true)
	viper.SetDefault("file_transfer", true)
	viper.SetDefault("exec_cmds", false)

	err = viper.ReadInConfig()
	if err != nil {
		log.Println("Error reading config file", err)
		viper.SafeWriteConfigAs(path)
		log.Println("Generated default capabilities file")
	} else {
		log.Println("Loaded device capabilities")
	}

	err = viper.Unmarshal(&caps)
	log.Println(caps)
	return caps, err
}
