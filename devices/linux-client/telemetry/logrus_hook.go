package telemetry

import (
	"fmt"
	"github.com/antmicro/rdfm/helpers"

	log "github.com/sirupsen/logrus"
)

type LogrusHook struct {
	levels        []log.Level
	telemetryChan chan<- LogEntry
}

func ConfigureLogrusHook(config string, ch chan<- LogEntry) error {
	hook := LogrusHook{}
	err := hook.determineLevelFromConfig(config)
	if err != nil {
		return err
	}
	hook.setChannel(ch)
	log.AddHook(&hook)
	return nil
}

func (hook *LogrusHook) setChannel(ch chan<- LogEntry) {
	hook.telemetryChan = ch
}

func (hook *LogrusHook) Levels() []log.Level {
	return hook.levels
}

func (hook *LogrusHook) Fire(entry *log.Entry) error {
	go func() {
		hook.telemetryChan <- MakeLogEntry(
			helpers.TimeToServerTime(entry.Time),
			fmt.Sprintf("RDFM-%s", entry.Level.String()),
			entry.Message,
		)
	}()
	return nil
}

var logLevels = [...]log.Level{
	log.PanicLevel,
	log.FatalLevel,
	log.ErrorLevel,
	log.WarnLevel,
	log.InfoLevel,
	log.DebugLevel,
	log.TraceLevel,
}

func (hook *LogrusHook) determineLevelFromConfig(config string) error {
	lvl, err := log.ParseLevel(config)
	if err != nil {
		return err
	}

	for _, l := range logLevels {
		if lvl >= l {
			hook.levels = append(hook.levels, l)
		}
	}
	return nil
}
