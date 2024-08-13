package daemon

import log "github.com/sirupsen/logrus"

type LoggerHook struct{}

func (hook *LoggerHook) Levels() []log.Level {
	return []log.Level{
		log.InfoLevel,
		log.ErrorLevel,
		log.FatalLevel,
		log.PanicLevel,
		log.WarnLevel,
		log.TraceLevel,
	}
}

func (hook *LoggerHook) Fire(entry *log.Entry) error {
	// fmt.Println("hook caught:", entry.Message)
	return nil
}
