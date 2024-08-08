package telemetry

import (
	"fmt"
	"math/rand"
	"regexp"
	"sync"
	"testing"
	"time"
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

	err := lm.StartTask(name, ld)
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

	lm.AddTask(name, rl)
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

	lm.AddTask(name, rl)
	lm.StartTask(name, ld)
	if err := lm.StartTask(name, ld); err == nil || !want.MatchString(err.Error()) {
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
	lm.AddTask(name, rl)
	if err := lm.AddTask(name, rl); err == nil || !want.MatchString(err.Error()) {
		t.Fatalf(`.AddTask("AlreadyExists") = %v, want match for %#q`, err, want)
	}
}

func FuzzRecurringLogger(f *testing.F) {
	lm := MakeLogManager()
	ld := LoggerArgs{}
	var rl RecurringLogger = recurringLogger

	f.Add("name")
	f.Fuzz(func(t *testing.T, name string) {
		lm.AddTask(name, rl)
		lm.StartTask(name, ld)
		lm.StopTask(name)
	})
}

func FuzzPersistentLogger(f *testing.F) {
	lm := MakeLogManager()
	ld := LoggerArgs{}
	var pl PersistentLogger = persistentLogger

	f.Add("name")
	f.Fuzz(func(t *testing.T, name string) {
		lm.AddTask(name, pl)
		lm.StartTask(name, ld)
		lm.StopTask(name)
	})
}

func FuzzRandomOrder(f *testing.F) {
	lm := MakeLogManager()

	rand.Seed(time.Now().UnixNano())

	funcs := []func(*LogManager, string){
		add,
		start,
		stop,
	}

	f.Add("name")
	f.Fuzz(func(t *testing.T, name string) {
		var wg sync.WaitGroup
		shuffledFuncs := shuffleFuncs(funcs)

		for _, f := range shuffledFuncs {
			wg.Add(1)
			go func(f func(*LogManager, string)) {
				defer wg.Done()
				f(lm, name)
				if rand.Float64() < 0.5 {
					f(lm, name)
				}
			}(f)
		}
		wg.Wait()
	})

}

func add(lm *LogManager, name string) {
	if randBool() {
		var pl PersistentLogger = persistentLogger
		lm.AddTask(name, pl)
	} else {
		var rl RecurringLogger = recurringLogger
		lm.AddTask(name, rl)
	}
}

func start(lm *LogManager, name string) {
	ld := LoggerArgs{}
	lm.StartTask(name, ld)
}

func stop(lm *LogManager, name string) {
	lm.StopTask(name)
}

func shuffleFuncs(funcs []func(*LogManager, string)) []func(*LogManager, string) {
	shuffled := make([]func(*LogManager, string), len(funcs))
	copy(shuffled, funcs)
	rand.Shuffle(len(shuffled), func(i, j int) {
		shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
	})
	return shuffled
}
