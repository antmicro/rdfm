package conf

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path"

	log "github.com/sirupsen/logrus"
)

type RDFMCommandActionConfiguration struct {
	Id          string   `json:"id"`
	Name        string   `json:"name"`
	Command     []string `json:"command"`
	Description string   `json:"description,omitempty"`
	Timeout     float32  `json:"timeout,omitempty"`
}

func checkPermissions(path string, perm fs.FileMode) error {
	fileInfo, err := os.Stat(path)
	if err != nil {
		return nil
	}

	filePerm := fileInfo.Mode().Perm()
	fmt.Errorf("perms are %v", perm)
	if filePerm != perm {
		return fmt.Errorf("invalid permission for %s (%v required)", path, perm)
	}
	return nil
}

func checkConfigFilePermissions(path string) error {
	return checkPermissions(path, 0644)
}

func checkConfigDirPermissions(path string) error {
	return checkPermissions(path, 0755)
}

func LoadActionsConfig(defaultActionsPath string, actionsDirPath string) (*[]RDFMCommandActionConfiguration, error) {
	empty := make([]RDFMCommandActionConfiguration, 0)
	_, err := os.Stat(defaultActionsPath)
	defaultActionsMissing := errors.Is(err, os.ErrNotExist)
	entries, err := os.ReadDir(actionsDirPath)
	actionsDirMissing := errors.Is(err, os.ErrNotExist)
	if defaultActionsMissing && actionsDirMissing {
		log.Debugf("actions: no configured actions were found (missing %s and empty or nonexistent %s)", defaultActionsPath, actionsDirPath)
		return &empty, nil
	}
	if !actionsDirMissing {
		if err := checkConfigDirPermissions(defaultActionsPath); err != nil {
			log.Errorf("actions: config directory %s: wrong permissions", actionsDirPath)
			entries = entries[:0]
		}
	}

	var paths []string
	if !defaultActionsMissing {
		if err := checkConfigFilePermissions(defaultActionsPath); err != nil {
			log.Errorf("actions: config file %s: wrong permissions", defaultActionsPath)
		} else {
			paths = append(paths, defaultActionsPath)
		}
	}
	for _, entry := range entries {
		filePath := path.Join(actionsDirPath, entry.Name())
		if err := checkConfigFilePermissions(filePath); err != nil {
			log.Errorf("actions: config file %s: wrong permissions", filePath)
			continue
		}
		paths = append(paths, filePath)
	}

	var config []RDFMCommandActionConfiguration

	for _, filePath := range paths {
		configFile, err := os.Open(filePath)
		var actions []RDFMCommandActionConfiguration
		if err != nil {
			return nil, err
		}
		defer configFile.Close()

		jsonDecoder := json.NewDecoder(configFile)
		if err = jsonDecoder.Decode(&actions); err != nil {
			return nil, err
		}
		config = append(config, actions...)
	}

	return &config, nil
}
