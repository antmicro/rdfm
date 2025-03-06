package main

import (
	"bytes"
	"time"
)

// A synchronous wrapper for getting the stats for a certain time.Duration in the form of bytes.Buffer
func CollectFor(ds *DriverSet, duration time.Duration) *bytes.Buffer {
	buf := &bytes.Buffer{}
	_, done := Collect(ds, buf)
	time.Sleep(duration)
	close(done)
	return buf
}

// A wrapper for initializing DriverSet
func Init(args ...string) (*DriverSet, error) {
	ds := &DriverSet{}
	if err := ds.Init(args); err != nil {
		return nil, err
	}
	return ds, nil
}
