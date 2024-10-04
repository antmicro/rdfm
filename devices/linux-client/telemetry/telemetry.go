package telemetry

import (
	"fmt"
	"sync"
	"time"

	"github.com/antmicro/rdfm/telemetry/conf"
	log "github.com/sirupsen/logrus"
)

type LoggerContext struct {
	Args LoggerArgs // Arguments

	Timeout time.Duration
	Logs    chan<- LogEntry
	Done    <-chan struct{} // Should only be used by a function of type PersistentLoggerFunc

}

/*** Logger function types ***/

/* Recurring logger function */
type RecurringLogger func(ctx LoggerContext)

/*
Purpose:
	Designed for one-time, periodic data collection,
	scheduled by the manager.
Bahavior:
	Logs should be collected promptly and the function
	should not block for extended periods. Prolonged blocking
	can result in missed log intervals.
*/

/* Persistent logger function */
type PersistentLogger func(ctx LoggerContext)

/*
Purpose:
	Suitable for stream-based log data, where logging begins
	once and continues until explicitly stopped. Not-scheduled,
	needs to take care of its own termination.
Behavior:
	Requires continuous cooperation with the scheduler. The logging
	goroutine should terminate when `ctx.Done` is signaled.
*/

type Logger interface {
	log(ctx LoggerContext)
}

func (r RecurringLogger) log(ctx LoggerContext) {
	r(ctx)
}

func (p PersistentLogger) log(ctx LoggerContext) {
	go p(ctx)
}

type logTask struct {
	done     chan struct{}
	logs     chan LogEntry
	interval time.Duration
	logger   Logger
	args     LoggerArgs

	mu      sync.Mutex
	running bool
}

func (task *logTask) runRecurringLogger(ctx LoggerContext) {
	ticks := time.Tick(task.interval)

loop:
	for {
		select {
		case <-ticks:
			task.logger.log(ctx)
		case <-task.done:
			break loop
		}
	}
}

func (task *logTask) runPersistentLogger(ctx LoggerContext) {
	done := make(chan struct{})
	ctx.Done = done
	task.logger.log(ctx)

loop:
	for {
		select {
		case <-task.done:
			close(done)
			break loop
		}
	}
}

func (task *logTask) start() {
	task.mu.Lock()
	defer task.mu.Unlock()

	if task.running {
		return
	}

	task.running = true
	ctx := LoggerContext{
		Args:    task.args,
		Done:    nil,
		Logs:    task.logs,
		Timeout: task.interval,
	}

	switch task.logger.(type) {
	case RecurringLogger:
		go task.runRecurringLogger(ctx)
	case PersistentLogger:
		go task.runPersistentLogger(ctx)
	}

	task.running = true
}

func (task *logTask) stop() {
	task.mu.Lock()
	defer task.mu.Unlock()

	if !task.running {
		return
	}
	close(task.done)
	task.running = false
}

func (task *logTask) isRunning() bool {
	task.mu.Lock()
	defer task.mu.Unlock()
	return task.running
}

type LogManager struct {
	tasks map[string]*logTask
	mu    sync.Mutex
}

func MakeLogManager() *LogManager {
	return &LogManager{
		tasks: make(map[string]*logTask),
	}
}

func (manager *LogManager) AddTask(name string, logger Logger, interval time.Duration) error {
	manager.mu.Lock()
	defer manager.mu.Unlock()

	if _, exists := manager.tasks[name]; exists {
		return fmt.Errorf("task \"%s\" already exists", name)
	}
	var task *logTask
	switch logger.(type) {
	case RecurringLogger:
		task = &logTask{logger: logger, interval: interval}
	case PersistentLogger:
		task = &logTask{logger: logger, interval: 0}
	}
	manager.tasks[name] = task

	return nil
}

func (manager *LogManager) StartTask(name string, args LoggerArgs, logs chan LogEntry) error {
	manager.mu.Lock()
	defer manager.mu.Unlock()

	if task, exists := manager.tasks[name]; exists {
		if task.isRunning() {
			return fmt.Errorf("task \"%s\" is already running", name)
		}
		task.args = args
		task.done = make(chan struct{})
		task.logs = logs
		task.start()
	} else {
		return fmt.Errorf("task \"%s\" does not exist", name)
	}
	return nil
}

func (manager *LogManager) StopTask(name string) error {
	manager.mu.Lock()
	defer manager.mu.Unlock()

	if task, exists := manager.tasks[name]; exists {
		if task.isRunning() {
			task.stop()
		} else {
			return fmt.Errorf("task \"%s\" is not running", name)
		}
	} else {
		return fmt.Errorf("task \"%s\" does not exist", name)
	}

	return nil
}

// Utility function that starts all the loggers within the provided map
func StartRecurringProcessLoggers(lm *LogManager, c *map[string]conf.RDFMLoggerConfiguration) chan LogEntry {
	logs := make(chan LogEntry)
	if c == nil {
		return logs
	}
	for k, v := range *c {
		err := lm.AddTask(
			k,
			RecurringProcessLogger,
			time.Millisecond*time.Duration(v.Tick),
		)
		if err != nil {
			log.Printf("Failed to start recurring process logger %s: %s", k, err.Error())
			continue
		}

		args := LoggerArgs{k, v.Path, v.Args}
		err = lm.StartTask(k, args, logs)

		if err != nil {
			log.Error(err)
		}
	}
	return logs
}

// Utilty function that tries to stop all the loggers within the provided map
func StopLoggers(lm *LogManager, c *map[string]conf.RDFMLoggerConfiguration) {
	for k := range *c {
		err := lm.StopTask(k)
		if err != nil {
			log.Printf("Failed to stop logger %s: %s", k, err.Error())
		}
	}
}
