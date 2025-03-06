package main

import (
	"fmt"
	"io"
	"time"
)

// Collects data and prints it as CSV records to io.Writer.
func Collect(ds *DriverSet, dest io.Writer) (chan string, chan struct{}) {
	labels := make(chan string)
	done := make(chan struct{})

	ticks := time.Tick(time.Second)
	tags := ds.Tags()

	fmt.Fprint(dest, ds.Header(), "tags\r\n")
	go func() {
		for {
			select {
			case <-ticks:
				ds.Update()
				fmt.Fprint(dest, ds, tags.CSV(), "\r\n")
				tags = make(Tags)
			case label := <-labels:
				tags.Concat("label", label)
			case <-done:
				return
			}
		}
	}()

	return labels, done
}
