package conf

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"

	log "github.com/sirupsen/logrus"
)

type RDFMCommandActionConfiguration struct {
	Id          string   `json:"id"`
	Name        string   `json:"name"`
	Command     []string `json:"command"`
	Description string   `json:"description,omitempty"`
	Timeout     float32  `json:"timeout,omitempty"`
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

func LoadActionsConfig(path string) (*[]RDFMCommandActionConfiguration, error) {
	if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
		log.Warnf("actions: no configured actions were found (missing %s)", path)
		empty := make([]RDFMCommandActionConfiguration, 0)
		return &empty, nil
	}

	if err := checkConfigFilePermissions(path); err != nil {
		log.Error("actions: config file: wrong permissions")
		return nil, err
	}

	var config []RDFMCommandActionConfiguration

	configFile, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer configFile.Close()

	jsonDecoder := json.NewDecoder(configFile)
	if err = jsonDecoder.Decode(&config); err != nil {
		return nil, err
	}

	return &config, nil
}
