package conf

import (
	"bufio"
	"errors"
	"os"

	log "github.com/sirupsen/logrus"
)

var (
	ErrDeviceIdInvalid = errors.New("Device ID invalid or corrupted")
)

// Try loading the device identifier from the device_id file.
func LoadDeviceId() (*string, error) {
	file, err := os.Open(RdfmDeviceIdPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var deviceId *string = nil
	sc := bufio.NewScanner(file)
	for sc.Scan() {
		if deviceId != nil {
			log.Warnln("device_id file has multiple lines; remaining lines will be ignored.")
			break
		}
		line := sc.Text()
		deviceId = &line
	}
	if err = sc.Err(); err != nil {
		return nil, err
	}
	if deviceId == nil {
		return nil, ErrDeviceIdInvalid
	}
	if len(*deviceId) == 0 {
		return nil, ErrDeviceIdInvalid
	}
	return deviceId, nil
}

// Save a given identifier to the device_id file.
func SaveDeviceId(id string) error {
	bytes := []byte(id)
	err := os.WriteFile(RdfmDeviceIdPath, bytes, 0644)
	return err
}
