package daemon

import (
	"context"
	"fmt"
	"time"

	"github.com/antmicro/rdfm/devices/linux-client/conf"
	"github.com/antmicro/rdfm/devices/linux-client/telemetry"

	log "github.com/sirupsen/logrus"
)

const TELEMETRY_LOOP_RECOVERY_INTERVAL_S = 60
const TELEMETRY_RING_SIZE = 50

func (d *Device) logSendLoop(cancelCtx context.Context, msgOutCh <-chan telemetry.Message) {
	for {
		select {
		case <-cancelCtx.Done():
			log.Println("Telemetry: logSendLoop: received cancellation signal, closing")
			return
		default:
			err := d.kafkaRunner.ClientLoop(
				cancelCtx,
				msgOutCh,
			)
			if err != nil {
				recoveryTime := TELEMETRY_LOOP_RECOVERY_INTERVAL_S * time.Second
				log.Println("Telemetry: logSendLoop: KafkaRunner ClientLoop failed with", err)
				log.Println("Telemetry: logSendLoop: Rerunning ClientLoop in", recoveryTime)
				time.Sleep(recoveryTime)
			} else {
				log.Debug("Telemetry: logSendLoop: KafkaRunner ClientLoop graceful exit, rerunning")
			}
		}
	}
}

func (d *Device) telemetryLoop(cancelCtx context.Context) {
	if !d.rdfmCtx.RdfmConfig.TelemetryEnable {
		return
	}

	if d.rdfmCtx.RdfmConfig.TelemetryBatchSize < 512 {
		log.Warnln("Telemetry: the minimum value of TelemetryBatchSize is 512, falling back to default:",
			conf.DEFAULT_TELEMETRY_BATCH_SIZE)
		d.rdfmCtx.RdfmConfig.TelemetryBatchSize = conf.DEFAULT_TELEMETRY_BATCH_SIZE
	}

	// telemetry.LogEntry adheres to the telemetry.Message
	msgInCh := telemetry.StartRecurringProcessLoggers(
		d.logManager,
		d.rdfmCtx.RdfmTelemetryConfig,
	)
	msgOutCh := make(chan telemetry.Message, TELEMETRY_RING_SIZE)
	messageRingBuffer := telemetry.NewRingBuffer[telemetry.Message](msgInCh, msgOutCh)
	go messageRingBuffer.Run()

	err := telemetry.ConfigureLogrusHook(d.rdfmCtx.RdfmConfig.TelemetryLogLevel, msgInCh)
	if err != nil {
		log.Warnln("Telemetry: logrus hook configuration:", err.Error())
	}

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
			case <-cancelCtx.Done():
				return
			default:
			}
			log.Println("Telemetry: main loop recovery from", info)
			recoveryTime := TELEMETRY_LOOP_RECOVERY_INTERVAL_S * time.Second
			log.Println("Rerunning telemetry loop in", recoveryTime)
			time.Sleep(recoveryTime)
			loop()
		}()

		d.logSendLoop(cancelCtx, msgOutCh)
	}
	loop()
}
