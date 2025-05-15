package daemon

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	log "github.com/sirupsen/logrus"

	packages "github.com/antmicro/rdfm/devices/linux-client/daemon/packages"
)

const MIN_RETRY_INTERVAL = 1
const MAX_RETRY_INTERVAL = 60

func (d *Device) checkUpdate() error {
	metadata, err := d.collectMetadata()
	if err != nil {
		return err
	}
	log.Println("Metadata to check updates: ", metadata)

	serializedMetadata, err := json.Marshal(metadata)
	if err != nil {
		return errors.New("Failed to serialize metadata: " + err.Error())
	}
	endpoint := fmt.Sprintf("%s/api/v1/update/check",
		d.rdfmCtx.RdfmConfig.ServerURL)
	req, _ := http.NewRequest("POST", endpoint,
		bytes.NewBuffer(serializedMetadata),
	)
	req.Header.Set("Content-Type", "application/json")
	deviceToken, err := d.getDeviceToken()
	if err != nil {
		return errors.New("Failed to fetch the device token: " + err.Error())
	}
	req.Header.Add("Authorization", "Bearer token="+deviceToken)

	log.Println("Checking updates...")

	var client *http.Client
	client = &http.Client{Transport: d.httpTransport}
	res, err := client.Do(req)
	if err != nil {
		return errors.New("Update check request failed: " + err.Error())
	}
	defer res.Body.Close()

	switch res.StatusCode {
	case 200:
		log.Println("An update is available")
		var pkg packages.Package
		bodyBytes, err := io.ReadAll(res.Body)
		if err != nil {
			return errors.New("Failed to get package metadata from response body: " + err.Error())
		}
		err = json.Unmarshal(bodyBytes, &pkg)
		if err != nil {
			return errors.New("Failed to deserialize package metadata: " + err.Error())
		}

		log.Printf("Installing package from %s...\n", pkg.Uri)
		err = d.rdfmCtx.InstallArtifact(pkg.Uri)
		if err != nil {
			log.Println("Failed to install package",
				pkg.Id, err)
			// TODO: Do something in case of failure
		}
	case 204:
		log.Println("No updates are available")
	case 400:
		return errors.New("Device metadata is missing device type and/or software version")
	case 401:
		return errors.New("Device did not provide authorization data, or the authorization has expired")
	default:
		return errors.New("Unexpected status code from the server: " + res.Status)
	}
	return nil
}

func (d *Device) updateCheckerLoop(cancelCtx context.Context) {
	var err error
	var info string

	// Recover the goroutine if it panics
	defer func() {
		if r := recover(); r != nil {
			info = fmt.Sprintf("error: %v", r)
		} else {
			info = "unexpected goroutine completion"
		}
		select {
		case <-cancelCtx.Done():
			return
		default:
		}
		log.Println("Updater loop recovery from", info)
		d.updateCheckerLoop(cancelCtx)
	}()

	for {
		err = d.checkUpdate()
		if err != nil {
			log.Println("Update check failed:", err)
		}
		updateDuration := time.Duration(d.rdfmCtx.RdfmConfig.UpdatePollIntervalSeconds) * time.Second
		log.Printf("Next update check in %s\n", updateDuration)
		select {
		case <-time.After(time.Duration(updateDuration)):
		case <-cancelCtx.Done():
			return
		}
	}
	panic(err)
}
