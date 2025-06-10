package telemetry

import (
	"fmt"
	"math/rand"
	"reflect"
	"regexp"
	"testing"
	"time"

	log "github.com/sirupsen/logrus"
)

func nop() {
	i := 0
	switch i {
	case 0:
	case 1:
		fmt.Println("nop")
	}
}

func persistentLogger(ctx LoggerContext) {
	ticks := time.Tick(time.Millisecond)
	for {
		select {
		case <-ticks:
			nop()
		case <-ctx.Done:
			return
		}
	}
}

func recurringLogger(ctx LoggerContext) {
	nop()
}

func randBool() bool {
	rand.Seed(time.Now().UnixNano())
	return rand.Intn(2) == 1
}

func TestDoesNotExist(t *testing.T) {
	lm := MakeLogManager()
	ld := LoggerArgs{}

	name := "DoesntExist"
	want := regexp.MustCompile(`\btask "` + name + `" does not exist\b`)

	err := lm.StartTask(name, ld, nil)
	if err == nil || !want.MatchString(err.Error()) {
		t.Fatalf(`.StartTask("DoesntExist") = %v, want match for %#q`, err, want)
	}

	if err = lm.StopTask(name); err == nil || !want.MatchString(err.Error()) {
		t.Fatalf(`.StopTask("DoesntExist") = %v, want match for %#q`, err, want)
	}
}

func TestNotRunning(t *testing.T) {
	lm := MakeLogManager()

	name := "NotRunning"
	want := regexp.MustCompile(`\btask "` + name + `" is not running\b`)
	var rl RecurringLogger = func(ctx LoggerContext) {
		nop()
	}

	lm.AddTask(name, rl, time.Millisecond)
	if err := lm.StopTask(name); err == nil || !want.MatchString(err.Error()) {
		t.Fatalf(`.StopTask("NotRunning") = %v, want match for %#q`, err, want)

	}
}

func TestAlreadyRunning(t *testing.T) {
	lm := MakeLogManager()
	ld := LoggerArgs{}

	name := "AlreadyRunning"
	want := regexp.MustCompile(`\btask "` + name + `" is already running\b`)
	var rl RecurringLogger = func(ctx LoggerContext) {
		nop()
	}

	lm.AddTask(name, rl, time.Millisecond)
	lm.StartTask(name, ld, nil)
	if err := lm.StartTask(name, ld, nil); err == nil || !want.MatchString(err.Error()) {
		t.Fatalf(`.StartTask("AlreadyRunning") = %v, want match for %#q`, err, want)
	}
	lm.StopTask(name)
}

func TestAlreadyExists(t *testing.T) {
	lm := MakeLogManager()

	name := "AlreadyExists"
	want := regexp.MustCompile(`\btask "` + name + `" already exists\b`)
	var rl RecurringLogger = func(ctx LoggerContext) {
		nop()
	}
	lm.AddTask(name, rl, time.Millisecond)
	if err := lm.AddTask(name, rl, time.Millisecond); err == nil || !want.MatchString(err.Error()) {
		t.Fatalf(`.AddTask("AlreadyExists") = %v, want match for %#q`, err, want)
	}
}

func TestDetermineLevel(t *testing.T) {
	var want error = nil

	hook1 := LogrusHook{}
	if err := hook1.determineLevelFromConfig("FATAL"); err != nil {
		t.Fatalf(`hook1.determineLevelFromConfig("FATAL") = %v, want match for %#q`, err, want)
	}
	want1 := []log.Level{
		log.PanicLevel,
		log.FatalLevel,
	}
	if !reflect.DeepEqual(hook1.Levels(), want1) {
		t.Fatalf(`hook1.Levels() = %v, want match for %#q`, hook1.Levels(), want1)
	}

	hook2 := LogrusHook{}
	want2 := []log.Level{
		log.PanicLevel,
		log.FatalLevel,
		log.ErrorLevel,
		log.WarnLevel,
		log.InfoLevel,
		log.DebugLevel,
		log.TraceLevel,
	}
	if err := hook2.determineLevelFromConfig("trace"); err != nil {
		t.Fatalf(`hook2.determineLevelFromConfig("trace") = %v, want match for %#q`, err, want)
	}
	if !reflect.DeepEqual(hook2.Levels(), want2) {
		t.Fatalf(`hook2.Levels() = %v, want match for %#q`, hook2.Levels(), want2)
	}

	hook3 := LogrusHook{}
	if err := hook3.determineLevelFromConfig("Panic"); err != nil {
		t.Fatalf(`hook3.determineLevelFromConfig("Panic") = %v, want match for %#q`, err, want)
	}
	want3 := []log.Level{
		log.PanicLevel,
	}
	if !reflect.DeepEqual(hook3.Levels(), want3) {
		t.Fatalf(`hook3.Levels() = %v, want match for %#q`, hook1.Levels(), want3)
	}

	hook4 := LogrusHook{}
	wantErr := regexp.MustCompile(`not a valid logrus Level: "WRONG"`)
	if err := hook4.determineLevelFromConfig("WRONG"); err == nil || !wantErr.MatchString(err.Error()) {
		t.Fatalf(`hook4.determineLevelFromConfig("WRONG") = %v, want match for %#q`, err, wantErr)
	}
}

func TestFireLogs(t *testing.T) {
	logs := make(chan LogEntry, 1)
	var wantErr error = nil

	err := ConfigureLogrusHook("WARN", logs)
	if err != nil {
		t.Fatalf(`ConfigureLogrusHook("WARN", logs) = %v, want match for %#q`, err, wantErr)
	}

	warn := "foo"
	var want int = 1

	log.Warn(warn)
	time.Sleep(time.Millisecond) // Sleep for a millisecond to let the buffered channel receive a log entry

	if l := len(logs); l != want {
		t.Fatalf(`1: len(logs) = %v, want match for %#q`, l, want)
	}

	entry := <-logs
	wantEntry := regexp.MustCompile(warn)
	if !wantEntry.MatchString(entry.Entry) {
		t.Fatalf(`entry.Entry = %v, want match for %#q`, entry.Entry, wantEntry)
	}

	want = 0

	log.Info("bar")
	time.Sleep(time.Millisecond)

	if l := len(logs); l != want {
		t.Fatalf(`2: len(logs) = %v, want match for %#q`, l, want)
	}

	want = 1

	log.Error("baz")
	time.Sleep(time.Millisecond)

	if l := len(logs); l != want {
		t.Fatalf(`3: len(logs) = %v, want match for %#q`, l, want)
	}
}
