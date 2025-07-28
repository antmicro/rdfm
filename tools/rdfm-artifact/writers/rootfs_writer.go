package writers

import (
	"github.com/antmicro/rdfm/tools/rdfm-artifact/deltas"
	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"
)

type RootfsArtifactWriter struct {
	ArtifactWriter
}

func NewRootfsArtifactWriter(outputPath string) RootfsArtifactWriter {
	return RootfsArtifactWriter{
		ArtifactWriter{
			pathToDeltas: "",
			outputPath:   outputPath,
			args: awriter.WriteArtifactArgs{
				Format:     rdfmArtifactFormat,
				Version:    rdfmArtifactVersion,
				Updates:    &awriter.Updates{},
				TypeInfoV3: &artifact.TypeInfoV3{},
			},
		},
	}
}

// Below, "Updates" is equivalent to "payload"
// The "composer" is responsible for adding files that are relevant to a certain update type
// Only support two for now - full rootfs image and delta rootfs image payloads
func (d *RootfsArtifactWriter) WithFullRootfsPayload(pathToRootfs string) error {
	checksum, err := calculatePayloadChecksum(pathToRootfs)
	if err != nil {
		return err
	}

	// Set the proper provides value when writing artifacts
	if d.args.TypeInfoV3.ArtifactProvides != nil {
		d.args.TypeInfoV3.ArtifactProvides[rdfmRootfsProvidesChecksum] = checksum
		d.args.TypeInfoV3.ArtifactProvides[rdfmRootfsProvidesVersion] = d.args.Provides.ArtifactName
	} else {
		d.WithPayloadProvides(map[string]string{
			rdfmRootfsProvidesChecksum: checksum,
			rdfmRootfsProvidesVersion:  d.args.Provides.ArtifactName,
		})
	}

	d.args.Updates.Updates = []handlers.Composer{
		handlers.NewRootfsV3(pathToRootfs),
	}
	return nil
}

func (d *ArtifactWriter) WithDeltaRootfsPayload(baseArtifactPath string, targetArtifactPath string) error {
	// First, clone the target artifact metadata into the writer
	// This is so we get an identical set of provides/depends, as if we had installed
	// a full rootfs artifact.
	err := d.cloneMetaFromArtifact(targetArtifactPath)
	if err != nil {
		return err
	}

	// Additionally, set the dependency values.
	// This ensures that we don't install a delta onto a rootfs that is not the base
	// used for creating them.
	provides, err := readArtifactPayloadProvides(baseArtifactPath)
	if err != nil {
		return err
	}
	if d.args.TypeInfoV3.ArtifactDepends != nil {
		d.args.TypeInfoV3.ArtifactDepends[rdfmRootfsProvidesChecksum] = provides[rdfmRootfsProvidesChecksum]
	} else {
		d.WithPayloadDepends(map[string]string{
			rdfmRootfsProvidesChecksum: provides[rdfmRootfsProvidesChecksum],
		})
	}

	p := deltas.NewArtifactDelta(baseArtifactPath, targetArtifactPath)
	deltaFilename, err := p.Delta()
	if err != nil {
		return err
	}
	d.pathToDeltas = deltaFilename

	// The deltas are saved directly as a payload in the artifact
	d.args.Updates.Updates = []handlers.Composer{
		handlers.NewRootfsV3(d.pathToDeltas),
	}
	return nil
}
