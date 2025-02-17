package deltas

import (
	"fmt"
	"os"

	"github.com/antmicro/rdfm/tools/rdfm-artifact/delta_engine"
	"github.com/antmicro/rdfm/tools/rdfm-artifact/extractors"
	"golang.org/x/sync/errgroup"
)

type ArtifactDelta struct {
	baseArtifactPath   string
	targetArtifactPath string
	outputDeltaPath    string
	deltaEngine        delta_engine.DeltaAlgorithmEngine
}

func NewArtifactDelta(basePath string, targetPath string, engine delta_engine.DeltaAlgorithmEngine) ArtifactDelta {
	return ArtifactDelta{
		baseArtifactPath:   basePath,
		targetArtifactPath: targetPath,
		outputDeltaPath:    "", // Set later during Delta()
		deltaEngine:        engine,
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

	targetImage := extractors.NewArtifactExtractor()
	if err := targetImage.Open(d.targetArtifactPath); err != nil {
		return "", err
	}

	var g errgroup.Group

	g.Go(func() error {
		// Extraction must happen on a separate goroutine
		err := baseImage.Extract()
		// Close immediately if an error occurs to avoid deadlock
		if err != nil {
			baseImage.Close()
		}
		return err
	})

	g.Go(func() error {
		// Same as above
		err := targetImage.Extract()
		if err != nil {
			targetImage.Close()
		}
		return err
	})

	g.Go(func() error {
		// Delta generation
		defer baseImage.Close()
		defer targetImage.Close()

		// Save the deltas to a temporary file
		// This is required, as RDFM expects a specific file name format for proper
		// detection of deltas
		f, err := os.CreateTemp(os.TempDir(), fmt.Sprintf("rootfs-image-delta-*"))
		if err != nil {
			return err
		}

		err = d.deltaEngine.Delta(baseImage.Reader(), targetImage.Reader(), f)
		f.Close()
		if err != nil {
			return err
		}

		// Change the filename, as RDFM requires the payload size in the filename,
		// but the payload size was unknown before the extraction end.
		newDeltaPath := fmt.Sprintf("%s.%d.%s", f.Name(), baseImage.PayloadSize(), d.deltaEngine.Name())
		err = os.Rename(f.Name(), newDeltaPath)
		if err != nil {
			return err
		}

		d.outputDeltaPath = newDeltaPath
		return nil
	})

	if err := g.Wait(); err != nil {
		return "", err
	}
	return d.outputDeltaPath, nil
}
