package deltas

import (
	"io"

	"github.com/antmicro/rdfm-artifact/updaters"
	"github.com/balena-os/librsync-go"
	"golang.org/x/sync/errgroup"
)

type ArtifactDelta struct {
	baseArtifactPath   string
	targetArtifactPath string
	deltaReader        *io.PipeReader
	deltaWriter        *io.PipeWriter
}

func NewArtifactDelta(basePath string, targetPath string) ArtifactDelta {
	r, w := io.Pipe()
	return ArtifactDelta{
		baseArtifactPath:   basePath,
		targetArtifactPath: targetPath,
		deltaReader:        r,
		deltaWriter:        w,
	}
}

// Calculate the delta between the rootfs images contained within the input artifacts
func (d *ArtifactDelta) Delta() error {
	baseImage := updaters.NewArtifactExtractor()
	if err := baseImage.Open(d.baseArtifactPath); err != nil {
		return err
	}
	defer baseImage.Close()

	targetImage := updaters.NewArtifactExtractor()
	if err := targetImage.Open(d.targetArtifactPath); err != nil {
		return err
	}
	defer targetImage.Close()

	var g errgroup.Group

	g.Go(func() error {
		// Extraction must happen on a separate goroutine
		return baseImage.Extract()
	})
	g.Go(func() error {
		// Same as above
		return targetImage.Extract()
	})
	g.Go(func() error {
		// Calculate the signature
		signature, err := librsync.Signature(baseImage.Reader(), io.Discard, DeltaBlockLength, DeltaStrongLength, DeltaSignatureType)
		if err != nil {
			d.deltaWriter.CloseWithError(err)
			return err
		}

		// Generate the deltas
		err = librsync.Delta(signature, targetImage.Reader(), d.deltaWriter)
		d.deltaWriter.CloseWithError(err)
		return err
	})

	return g.Wait()
}

// This returns a pipe that can be used to read the generated deltas
func (d *ArtifactDelta) Reader() *io.PipeReader {
	return d.deltaReader
}
