package telemetry

import (
	"github.com/antmicro/rdfm/devices/linux-client/protos"
	"time"
)

type Message interface {
	Topic() string
	Key() []byte
	Value(mac string) ([]byte, error)
	Time() time.Time
}

// Struct that's passed to a logger function within the LoggerContext
type LoggerArgs struct {
	Name string
	Path string
	Args []string
}

type LogEntry struct {
	Timestamp time.Time
	Name      string
	Entry     string
}

func MakeLogEntry(timestamp time.Time, name string, entry string) LogEntry {
	return LogEntry{
		Timestamp: timestamp,
		Name:      name,
		Entry:     entry,
	}
}

func (e LogEntry) Topic() string {
	return "" // Fallback to kgo.DefaultProduceTopic client param for now
}

func (e LogEntry) Key() []byte {
	return []byte(e.Name)
}

func (e LogEntry) Value(mac string) ([]byte, error) {
	return protos.CreateLog(mac, e.Timestamp, e.Entry)
}

func (e LogEntry) Time() time.Time {
	return e.Timestamp
}
