package app

import (
	"github.com/asaskevich/EventBus"
	"github.com/mendersoftware/mender/utils"
	"github.com/mendersoftware/progressbar"
)

var Bus = EventBus.New()

type ProgressWriter struct {
	progressWriter *utils.ProgressWriter
	bar            *progressbar.Bar
	lastUpdate     int
}

func NewProgressWriter(size int64) *ProgressWriter {
	return &ProgressWriter{
		progressWriter: utils.NewProgressWriter(size),
		bar:            progressbar.New(size),
	}
}

func (p *ProgressWriter) Write(data []byte) (int, error) {
	n, _ := p.progressWriter.Write(data)
	p.bar.Tick(int64(n))

	if p.bar.Percentage != p.lastUpdate {
		p.lastUpdate = p.bar.Percentage

		if p.bar.Percentage == 99 {
			Bus.Publish("progress", 100)
		} else {
			Bus.Publish("progress", p.bar.Percentage)
		}
	}

	return n, nil
}
