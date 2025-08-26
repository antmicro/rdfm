package telemetry

import (
	"bufio"
	"context"
	"io"
	"os/exec"
	"strings"
	"time"

	log "github.com/sirupsen/logrus"
)

func readFromPipe(pipe io.ReadCloser, ch chan string, ctx context.Context) {
	scanner := bufio.NewScanner(pipe)
	for scanner.Scan() {
		select {
		case <-ctx.Done():
			break
		default:
			ch <- scanner.Text()
		}
	}

	/* Err() returns any error that isn't io.EOF,
	so no need to take of that scenario */
	if err := scanner.Err(); err != nil {
		/* If the scanner happens to scan after process closure
		it errors out. Since the process is done executing
		returning quietly makes sense. */
		if !strings.Contains(err.Error(), "file already closed") {
			log.Error("readFromPipe:", err)
		}
	}
	close(ch)
}

/* RecurringProcessLogger */
// A function of type RecurringLogger that is able to be scheduled
// by LogManger to periodically run an executable and capture its
// output (stdout and stderr). It's set to timeout if its execution
// reaches task.interval (passed as ctx.Timeout).
var RecurringProcessLogger = RecurringLogger(
	func(ctx LoggerContext) {
		tctx, cancel := context.WithTimeout(context.Background(), ctx.Timeout)
		defer cancel()

		cmd := exec.CommandContext(tctx, ctx.Args.Path, ctx.Args.Args...)

		r, err := cmd.StdoutPipe()
		if err != nil {
			log.Errorf("logger %s: error creating stdout pipe: %v", ctx.Args.Name, err)
			return
		}

		re, err := cmd.StderrPipe()
		if err != nil {
			log.Errorf("logger %s: error creating stderr pipe: %v", ctx.Args.Name, err)
			return
		}

		stdoutCh := make(chan string)
		stderrCh := make(chan string)
		go readFromPipe(r, stdoutCh, tctx)
		go readFromPipe(re, stderrCh, tctx)

		if err = cmd.Start(); err != nil {
			log.Errorf("logger %s: error starting the process: %v", ctx.Args.Name, err)
			return
		}

		go func() {
			for {
				select {
				case stdoutLine, ok := <-stdoutCh:
					if ok {
						ctx.Logs <- MakeLogEntry(
							time.Now(),
							ctx.Args.Name,
							stdoutLine,
						)
					} else {
						stdoutCh = nil
					}
				case stderrLine, ok := <-stderrCh:
					if ok {
						ctx.Logs <- MakeLogEntry(
							time.Now(),
							ctx.Args.Name,
							stderrLine,
						)
					} else {
						stderrCh = nil
					}
				case <-tctx.Done():
					return
				}
			}
		}()

		if err := cmd.Wait(); err != nil {
			switch err.(type) {
			case *exec.ExitError:
				log.Errorf(
					"logger %s: %s: unsuccessful exit: %v",
					ctx.Args.Name,
					ctx.Args.Path,
					err,
				)
				ctx.Logs <- MakeLogEntry(
					time.Now(),
					ctx.Args.Name,
					string(err.(*exec.ExitError).Stderr),
				)
			default:
				log.Errorf(
					"logger %s: %s: %v",
					ctx.Args.Name,
					ctx.Args.Path,
					err,
				)
			}
		}
	})
