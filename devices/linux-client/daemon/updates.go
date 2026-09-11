package daemon

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/antmicro/rdfm/devices/linux-client/progress"
	"io"
	"net/http"
	"time"

	log "github.com/sirupsen/logrus"

	packages "github.com/antmicro/rdfm/devices/linux-client/daemon/packages"
)

const MIN_RETRY_INTERVAL = 1
const MAX_RETRY_INTERVAL = 60

func (d *Device) checkUpdate(cancelCtx context.Context) (*packages.Package, error) {
	metadata, err := d.collectMetadata()
	if err != nil {
		return nil, err
	}
	log.Println("Metadata to check updates: ", metadata)

	serializedMetadata, err := json.Marshal(metadata)
	if err != nil {
		return nil, errors.New("Failed to serialize metadata: " + err.Error())
	}
	endpoint := fmt.Sprintf("%s/api/v1/update/check",
		d.rdfmCtx.RdfmConfig.ServerURL)
	req, _ := http.NewRequest("POST", endpoint,
		bytes.NewBuffer(serializedMetadata),
	)
	req.Header.Set("Content-Type", "application/json")
	deviceToken, err := d.getDeviceToken(cancelCtx)
	if err != nil {
		return nil, errors.New("Failed to fetch the device token: " + err.Error())
	}
	req.Header.Add("Authorization", "Bearer token="+deviceToken)

	log.Println("Checking updates...")

	var client *http.Client
	client = &http.Client{Transport: d.httpTransport}
	res, err := client.Do(req)
	if err != nil {
		return nil, errors.New("Update check request failed: " + err.Error())
	}
	defer res.Body.Close()

	switch res.StatusCode {
	case 200:
		log.Println("An update is available")
		var pkg packages.Package
		bodyBytes, err := io.ReadAll(res.Body)
		if err != nil {
			return nil, errors.New("Failed to get package metadata from response body: " + err.Error())
		}
		err = json.Unmarshal(bodyBytes, &pkg)
		if err != nil {
			return nil, errors.New("Failed to deserialize package metadata: " + err.Error())
		}

		return &pkg, nil
	case 204:
		log.Println("No updates are available")
	case 400:
		return nil, errors.New("Device metadata is missing device type and/or software version")
	case 401:
		return nil, errors.New("Device did not provide authorization data, or the authorization has expired")
	default:
		return nil, errors.New("Unexpected status code from the server: " + res.Status)
	}
	return nil, nil
}

func (d *Device) updateCheckerLoop(cancelCtx context.Context, triggerUpdateCheck chan bool) {
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
		d.updateCheckerLoop(cancelCtx, triggerUpdateCheck)
	}()

	for {
		pkg, err := d.checkUpdate(cancelCtx)
		if err != nil {
			log.Errorln("Update check failed:", err)
		} else {
			log.Printf("Installing package from %s...\n", pkg.Uri)
			if err = d.rdfmCtx.InstallArtifact(pkg.Uri); err != nil {
				progress.Bus.Publish("failure")
				log.Errorf("Failed to install package %v: %s",
					pkg.Id, err.Error())
			} else {
				d.updateSoftwareVersion(cancelCtx)
				if err = d.rdfmCtx.RebootSystemIfNeeded(); err != nil {
					log.Errorln("Could not reboot:", err)
				}
			}
		}
		updateDuration := time.Duration(d.rdfmCtx.RdfmConfig.UpdatePollIntervalSeconds) * time.Second
		log.Printf("Next update check in %s\n", updateDuration)
		select {
		case <-time.After(time.Duration(updateDuration)):
		case <-cancelCtx.Done():
			return
		case <-triggerUpdateCheck:
			continue
		}
	}
	panic(err)
}
