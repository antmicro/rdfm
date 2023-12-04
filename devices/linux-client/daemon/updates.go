package daemon

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	packages "github.com/antmicro/rdfm/daemon/packages"
)

func (d *Device) checkUpdatesPeriodically() {
	devType, err := d.rdfmCtx.GetCurrentDeviceType()
	if err != nil {
		log.Println("Error getting current device type", err)
		return
	}
	swVer, err := d.rdfmCtx.GetCurrentArtifactName()
	if err != nil {
		log.Println("Error getting current software version", err)
		return
	}

	go func() {
		for {
			log.Println("Checking updates...")
			metadata := map[string]string{
				"rdfm.hardware.devtype": devType,
				"rdfm.software.version": swVer,
				"rdfm.hardware.macaddr": d.macAddr,
			}
			log.Println("Metadata to check updates: ", metadata)
			serializedMetadata, err := json.Marshal(metadata)
			if err != nil {
				log.Println("Failed to serialize metadata", err)
				return
			}
			endpoint := fmt.Sprintf("%s/api/v1/update/check",
				d.rdfmCtx.RdfmConfig.ServerURL)
			req, _ := http.NewRequest("POST", endpoint,
				bytes.NewBuffer(serializedMetadata),
			)
			req.Header.Set("Content-Type", "application/json")
			req.Header.Add("Authorization", "Bearer token="+d.deviceToken)
			client := &http.Client{}
			res, err := client.Do(req)
			if err != nil {
				log.Println("Failed to check updates from ", err)
				return
			}

			switch res.StatusCode {
			case 200:
				log.Println("An update is available")
				var pkg packages.Package
				bodyBytes, err := io.ReadAll(res.Body)
				defer res.Body.Close()
				if err != nil {
					log.Println("Failed to get package metadata from response body", err)
					return
				}
				err = json.Unmarshal(bodyBytes, &pkg)
				if err != nil {
					log.Println("Failed to deserialize package metadata", err)
					return
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
				log.Println("Device metadata is missing device type and/or software version")
			case 401:
				log.Println("Device did not provide authorization data, or the authorization has expired")
				err := d.authenticateDeviceWithServer()
				if err != nil {
					log.Println("Failed to autheniticate with the server", err)
				}
				continue
			}
			update_duration := time.Duration(d.rdfmCtx.RdfmConfig.UpdatePollIntervalSeconds) * time.Second
			log.Printf("Next update check in %s\n", update_duration)
			time.Sleep(time.Duration(update_duration))
		}
		log.Println("Stopped checking for updates")
	}()
}
