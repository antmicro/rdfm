package telemetry

// Struct that's passed to a logger function within the LoggerContext
type LoggerArgs struct {
	Placeholder bool // Easily extensible
}
