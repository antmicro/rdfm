package conf

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"

	log "github.com/sirupsen/logrus"
)

type RDFMLoggerConfiguration struct {
	Name string   `json:"name,omitempty"`
	Path string   `json:"path,omitempty"`
	Args []string `json:"args,omitempty"`
	Tick int      `json:"tick,omitempty"`
}

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

func LoadConfig(path string) (*map[string]RDFMLoggerConfiguration, error) {
	if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
		log.Warnf("telemetry: no configured loggers were found (missing %s)", path)
		empty := make(map[string]RDFMLoggerConfiguration)
		return &empty, nil
	}

	if err := checkConfigFilePermissions(path); err != nil {
		log.Error("telemetry: config file: wrong permissions")
		return nil, err
	}

	var config []RDFMLoggerConfiguration
	unique_config := map[string]RDFMLoggerConfiguration{}
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

	return &unique_config, nil
}
