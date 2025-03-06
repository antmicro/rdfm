package main

import (
	"fmt"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

// Maps CLI flags of drivers to their objects.
var flagDriver = map[string]Driver{
	"-t":   &TimeDriver{},
	"-cpu": &CpuDriver{},
	"-mem": &MemDriver{},
	"-fs":  &DiskDriver{},
}

// Driver interface is a generic wrapper for drivers.
// Drivers are objects collecting OS data for the resulting CSV.
type Driver interface {
	Init([]string) error // initializes the driver with given args
	Update() error       // updates data in the driver
	Tags() Tags          // returns constant metadata like total RAM
	Header() string      // get CSV header of the column(s)
	fmt.Stringer         // get CSV record of the data
}

// DriverSet is simply an array of drivers compliant with the Driver interface.
// It can be used as a single driver and exists for convenience.
type DriverSet []Driver

// Applies Init to all drivers in the set.
func (ds *DriverSet) Init(args []string) error {
	var i, first int
	var d, newd Driver
	var found bool

	for i = 0; i <= len(args); i++ {
		if i < len(args) {
			newd, found = flagDriver[args[i]]
		}
		if (found || i == len(args)) && d != nil {
			if err := d.Init(args[first:i]); err != nil {
				return err
			}
			*ds = append(*ds, d)
		}
		if found {
			d, first = newd, i+1
		}
	}
	return nil
}

// Applies Update to all drivers in the set.
func (ds *DriverSet) Update() error {
	for _, d := range *ds {
		if err := d.Update(); err != nil {
			return err
		}
	}
	return nil
}

// Returns union of tags from all drivers in the set.
func (ds *DriverSet) Tags() Tags {
	tags := make(Tags)

	for _, d := range *ds {
		tags.Join(d.Tags())
	}
	return tags
}

// Returns CSV header of all drivers in the set.
func (ds *DriverSet) Header() string {
	var s string

	for _, d := range *ds {
		s += fmt.Sprint(d.Header())
	}
	return s
}

// Returns CSV record of data from drivers in the set.
func (ds *DriverSet) String() string {
	var s string

	for _, d := range *ds {
		s += fmt.Sprint(d)
	}
	return s
}

// Time driver collects info on current time.
type TimeDriver time.Time

func (t *TimeDriver) Init([]string) error {
	return nil
}

func (t *TimeDriver) Update() error {
	*t = TimeDriver(time.Now())
	return nil
}

func (t *TimeDriver) Tags() Tags {
	return Tags{}
}

func (t *TimeDriver) Header() string {
	return "time,"
}

func (t *TimeDriver) String() string {
	return time.Time(*t).Format("2006-01-02 15:04:05") + ","
}

// CPU driver collects info on current time.
type CpuDriver struct {
	Total    float64   // mean CPU usage in the last second
	Percents []float64 // mean usage per core
	Hdr      string    // header of the column(s)
	All      bool      // indicates whether the total mean (.Total) is collected
}

func (c *CpuDriver) Init(args []string) error {
	if len(args) >= 1 && args[0] == "all" {
		c.All = true
	}

	c.Hdr = "cpu:all,"
	c.Update()

	for i := range c.Percents {
		c.Hdr += fmt.Sprint("cpu:", i, ",")
	}
	return nil
}

func (c *CpuDriver) Update() error {
	var sum float64

	p, err := cpu.Percent(time.Duration(0), true)
	if err != nil {
		return fmt.Errorf("could not obtain cpu info: %v", err)
	}

	for _, n := range p {
		sum += n
	}
	c.Total = sum / float64(len(p))

	if c.All {
		c.Percents = p
	}
	return nil
}

func (c *CpuDriver) Tags() Tags {
	return Tags{}
}

func (c *CpuDriver) Header() string {
	return c.Hdr
}

func (c *CpuDriver) String() string {
	var s string

	s = fmt.Sprint(c.Total, ",")
	for _, p := range c.Percents {
		s += fmt.Sprint(p, ",")
	}
	return s
}

// Memory driver collects info on RAM percent usage.
type MemDriver mem.VirtualMemoryStat

func (v *MemDriver) Init(args []string) error {
	return v.Update()
}

func (v *MemDriver) Update() error {
	u, err := mem.VirtualMemory()
	if err != nil {
		return fmt.Errorf("could not obtain mem info: %v", err)
	}
	*v = MemDriver(*u)
	return nil
}

func (v *MemDriver) Tags() Tags {
	return Tags{
		"total mem": fmt.Sprint(v.Total),
	}
}

func (v *MemDriver) Header() string {
	return "mem,"
}

func (v *MemDriver) String() string {
	return fmt.Sprint(v.UsedPercent, ",")
}

// Disk driver collects info on FS percent usage.
type DiskDriver struct {
	St   *disk.UsageStat
	Path string
}

func (d *DiskDriver) Init(args []string) error {
	if len(args) >= 1 {
		d.Path = args[0]
	} else {
		d.Path = "/"
	}

	return d.Update()
}

func (d *DiskDriver) Update() error {
	st, err := disk.Usage(d.Path)
	if err != nil {
		return fmt.Errorf("could not obtain disk info: %v", err)
	}
	d.St = st

	return nil
}

func (d *DiskDriver) Tags() Tags {
	return Tags{
		"total disk": fmt.Sprint(d.St.Total),
	}
}

func (d *DiskDriver) Header() string {
	return fmt.Sprint("fs:", d.Path, ",")
}

func (d *DiskDriver) String() string {
	return fmt.Sprint(d.St.UsedPercent, ",")
}
