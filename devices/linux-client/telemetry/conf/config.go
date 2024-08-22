package conf

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

type LoggerConfiguration struct {
	Name string   `json:"name,omitempty"`
	Path string   `json:"path,omitempty"`
	Args []string `json:"args,omitempty"`
	Tick int      `json:"tick,omitempty"`
}

type LoggerConfigurations map[string]LoggerConfiguration

func checkConfigFilePermissions(path string) error {
	fileInfo, err := os.Stat(path)
	if err != nil {
		return nil
	}

	filePerm := fileInfo.Mode().Perm()
	if filePerm != 0644 {
		return fmt.Errorf("invalid permission for config file %s (644 required)", path)
	}
	return nil
}

func Parse(path string) (LoggerConfigurations, error) {

	if err := checkConfigFilePermissions(path); err != nil {
		return nil, err
	}

	var config []LoggerConfiguration
	unique_config := LoggerConfigurations{}
	configFile, err := os.Open(path)
	if err != nil {
		return nil, err
	}

	jsonDecoder := json.NewDecoder(configFile)
	if err = jsonDecoder.Decode(&config); err != nil {
		return nil, err
	}

	for _, logger := range config {
		if logger.Name == "" {
			return nil, errors.New("missing required string parameter: \"name\"")
		}

		if logger.Path == "" {
			return nil, errors.New("missing required string parameter: \"path\"")
		}
		unique_config[logger.Name] = logger
	}

	return unique_config, nil
}
