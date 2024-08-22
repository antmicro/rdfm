package telemetry

// Struct that's passed to a logger function within the LoggerContext
type LoggerArgs struct {
	Name string
	Path string
	Args []string
}

type LogBatch struct {
	Batch []LogEntry `json:"batch"`
}

type LogEntry struct {
	Timestamp string `json:"device_timestamp"`
	Name      string `json:"name"`
	Entry     string `json:"entry"`
}
