package main

import (
	"flag"
	"fmt"
	"time"
)

var (
	cpuFlag  bool
	memFlag  bool
	tFlag    bool
	fsFlag   bool
	duration int
)

func main() {
	flag.BoolVar(&cpuFlag, "cpu", false, "report CPU usage")
	flag.BoolVar(&memFlag, "mem", false, "report memory usage")
	flag.BoolVar(&tFlag, "t", false, "include time")
	flag.BoolVar(&fsFlag, "fs", false, "report filesystem usage")
	flag.IntVar(&duration, "duration", 5, "time to gather data in seconds")
	flag.Parse()

	if !cpuFlag && !memFlag && !tFlag && !fsFlag {
		return
	}

	flags := make([]string, 0, 4)
	if cpuFlag {
		flags = append(flags, "-cpu")
	}
	if memFlag {
		flags = append(flags, "-mem")
	}
	if tFlag {
		flags = append(flags, "-t")
	}
	if fsFlag {
		flags = append(flags, "-fs")
	}

	ds, _ := Init(flags...)
	fmt.Println(CollectFor(ds, time.Duration(duration)*time.Second).String())
}
