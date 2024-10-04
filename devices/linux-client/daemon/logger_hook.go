package daemon

import (
	"fmt"
	"github.com/antmicro/rdfm/helpers"
	"github.com/antmicro/rdfm/telemetry"
	log "github.com/sirupsen/logrus"
)

var globalTelemetryChannel chan<- telemetry.LogEntry = nil

type LoggerHook struct{}

func (hook *LoggerHook) Levels() []log.Level {
	return []log.Level{
		log.InfoLevel,
		log.ErrorLevel,
		log.WarnLevel,
	}
}

func (hook *LoggerHook) Fire(entry *log.Entry) error {
	go func() {
		globalTelemetryChannel <- telemetry.MakeLogEntry(
			helpers.TimeToServerTime(entry.Time),
			fmt.Sprintf("RDFM-%s", entry.Level.String()),
			entry.Message,
		)
	}()
	return nil
}
