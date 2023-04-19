package writers

import (
	"os"

	"github.com/antmicro/rdfm-artifact/deltas"
	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"
)

// This is a simple wrapper for awriter for easier manipulation of artifact metadata
type ArtifactWriter struct {
	pathToDeltas string
	outputPath   string
	args         awriter.WriteArtifactArgs
}

func NewArtifactWriter(outputPath string) ArtifactWriter {
	return ArtifactWriter{
		pathToDeltas: "",
		outputPath:   outputPath,
		args: awriter.WriteArtifactArgs{
			Format:     rdfmArtifactFormat,
			Version:    rdfmArtifactVersion,
			Updates:    &awriter.Updates{},
			TypeInfoV3: &artifact.TypeInfoV3{},
		},
	}
}

func (d *ArtifactWriter) WithArtifactDepends(compatibleArtifacts []string, compatibleDevices []string, compatibleGroups []string) {
	d.args.Depends = &artifact.ArtifactDepends{
		ArtifactName:      compatibleArtifacts,
		CompatibleDevices: compatibleDevices,
		ArtifactGroup:     compatibleGroups,
	}
}

func (d *ArtifactWriter) WithArtifactProvides(artifactName string, artifactGroup string) {
	d.args.Provides = &artifact.ArtifactProvides{
		ArtifactName:  artifactName,
		ArtifactGroup: artifactGroup,
	}
}

func (d *ArtifactWriter) WithPayloadDepends(payloadDepends map[string]string) {
	v, err := artifact.NewTypeInfoDepends(payloadDepends)
	if err != nil {
		panic("invalid type info depends")
	}
	d.args.TypeInfoV3.ArtifactDepends = v
}

func (d *ArtifactWriter) WithPayloadProvides(payloadProvides map[string]string) {
	v, err := artifact.NewTypeInfoProvides(payloadProvides)
	if err != nil {
		panic("invalid type info provides")
	}
	d.args.TypeInfoV3.ArtifactProvides = v
}

func (d *ArtifactWriter) WithPayloadClearsProvides(payloadClearsProvides []string) {
	d.args.TypeInfoV3.ClearsArtifactProvides = payloadClearsProvides
}

// Below, "Updates" is equivalent to "payload"
// The "composer" is responsible for adding files that are relevant to a certain update type
// Only support two for now - full rootfs image and delta rootfs image payloads
func (d *ArtifactWriter) WithFullRootfsPayload(pathToRootfs string) {
	d.args.Updates.Updates = []handlers.Composer{
		handlers.NewRootfsV3(pathToRootfs),
	}
}

func (d *ArtifactWriter) WithDeltaRootfsPayload(baseArtifactPath string, targetArtifactPath string) error {
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

// Writes the artifact and saves it to the specified file
func (d *ArtifactWriter) Write() error {
	f, err := os.OpenFile(d.outputPath, os.O_CREATE|os.O_WRONLY, 0664)
	if err != nil {
		return err
	}
	defer f.Close()

	writer := awriter.NewWriter(f, artifact.NewCompressorNone())
	err = writer.WriteArtifact(&d.args)

	// Clean up temporaries from delta generation
	if d.pathToDeltas != "" {
		os.Remove(d.pathToDeltas)
	}
	return err
}
