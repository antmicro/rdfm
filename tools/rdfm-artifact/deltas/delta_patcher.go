package deltas

import (
	"fmt"
	"io"
	"os"

	"github.com/antmicro/rdfm-artifact/extractors"
	"github.com/balena-os/librsync-go"
	"golang.org/x/sync/errgroup"
)

type ArtifactDelta struct {
	baseArtifactPath   string
	targetArtifactPath string
	outputDeltaPath    string
}

func NewArtifactDelta(basePath string, targetPath string) ArtifactDelta {
	return ArtifactDelta{
		baseArtifactPath:   basePath,
		targetArtifactPath: targetPath,
		outputDeltaPath:    "",
	}
}

// Calculate the delta between the rootfs images contained within the input artifacts
// The deltas are saved to a temporary file with the correct name for support in RDFM
// Returns path to the temporary file containing raw deltas, or an error on failure.
func (d *ArtifactDelta) Delta() (string, error) {
	baseImage := extractors.NewArtifactExtractor()
	if err := baseImage.Open(d.baseArtifactPath); err != nil {
		return "", err
	}
	defer baseImage.Close()

	targetImage := extractors.NewArtifactExtractor()
	if err := targetImage.Open(d.targetArtifactPath); err != nil {
		return "", err
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
			return err
		}

		// Save the deltas to a temporary file
		// This is required, as RDFM expects a specific file name format for proper
		// detection of deltas
		f, err := os.CreateTemp(os.TempDir(), fmt.Sprintf("rootfs-image-delta-*.%d.delta", baseImage.PayloadSize()))
		if err != nil {
			return err
		}
		defer f.Close()
		d.outputDeltaPath = f.Name()

		// Generate the deltas
		return librsync.Delta(signature, targetImage.Reader(), f)
	})

	if err := g.Wait(); err != nil {
		return "", err
	}
	return d.outputDeltaPath, nil
}
