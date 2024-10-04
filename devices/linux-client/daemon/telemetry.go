package daemon

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/antmicro/rdfm/telemetry"
	"io"
	"net/http"
	"time"

	log "github.com/sirupsen/logrus"
)

const TELEMETRY_LOOP_RECOVERY_INTERVAL = 5

func (d *Device) sendLogBatch(batch telemetry.LogBatch, client *http.Client, endpoint string) error {
	serializedBatch, err := json.Marshal(batch)
	if err != nil {
		return errors.New("Failed to serialize log batch: " + err.Error())
	}

	deviceToken, err := d.getDeviceToken()
	if err != nil {
		return err
	}

	req, _ := http.NewRequest("POST", endpoint, bytes.NewBuffer(serializedBatch))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Add("Authorization", "Bearer token="+deviceToken)
	res, err := client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	if res.StatusCode != 200 {
		body, _ := io.ReadAll(res.Body)
		return errors.New(string(body))
	}

	return nil
}

func (d *Device) sendLogEntries(entries *[]telemetry.LogEntry, client *http.Client, endpoint string) error {
	return d.sendLogBatch(telemetry.MakeLogBatch(*entries), client, endpoint)
}

func (d *Device) logSendLoop(entries *[]telemetry.LogEntry, done chan bool, logs <-chan telemetry.LogEntry) {
	log.Println("Telemetry loop running")
	client := &http.Client{Transport: d.httpTransport}
	batchSize := d.rdfmCtx.RdfmConfig.TelemetryBatchSize
	endpoint := fmt.Sprintf("%s/api/v1/logs", d.rdfmCtx.RdfmConfig.ServerURL)

	for {
		select {
		case <-done:
			telemetry.StopLoggers(d.logManager, d.rdfmCtx.RdfmTelemetryConfig)
			err := d.sendLogEntries(entries, client, endpoint)
			if err != nil {
				log.Error("Telemetry log batch request failed: " + err.Error())
			}
			return
		case entry := <-logs:
			*entries = append(*entries, entry)
			if len(*entries) >= batchSize {
				err := d.sendLogEntries(entries, client, endpoint)
				if err != nil {
					log.Error("Telemetry log batch request failed: " + err.Error())
					// Panic whenever an error occurs to put the logging goroutine
					// on a timeout. The slice containing the log batch isn't lost.
					// Slice will be zeroed only after a succesful log transfer to
					// the management server. Adding the timeout prevents feedback
					// loops caused by calling hooked logrus functions from within
					// telemetry.
					panic(err)
				}
				// Zero the slice to make space for new entries.
				*entries = (*entries)[:0]
			}
		}
	}
}

func (d *Device) telemetryLoop(done chan bool) {
	if !d.rdfmCtx.RdfmConfig.TelemetryEnable {
		return
	}

	logs := telemetry.StartRecurringProcessLoggers(
		d.logManager,
		d.rdfmCtx.RdfmTelemetryConfig,
	)

	globalTelemetryChannel = logs
	log.AddHook(&LoggerHook{})

	entries := make([]telemetry.LogEntry, 0, d.rdfmCtx.RdfmConfig.TelemetryBatchSize)

	var info string
	var loop func()
	loop = func() {
		defer func() {
			if r := recover(); r != nil {
				info = fmt.Sprintf("error: %v", r)
			} else {
				info = "unexpected goroutine completion"
			}
			select {
			case <-done:
				return
			default:
			}
			log.Println("Telemetry loop recovery from", info)
			recoveryTime := TELEMETRY_LOOP_RECOVERY_INTERVAL * time.Second
			log.Println("Rerunning telemetry loop in", recoveryTime)
			time.Sleep(recoveryTime)
			loop()
		}()

		d.logSendLoop(&entries, done, logs)
	}
	loop()
}
