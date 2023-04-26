package writers

import (
	"errors"
	"io"
	"os"

	"github.com/antmicro/rdfm-artifact/deltas"
	"github.com/mendersoftware/mender-artifact/areader"
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
	d.withPayloadDependsTypeErased(payloadDepends)
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

func (d *ArtifactWriter) withPayloadDependsTypeErased(payloadDepends interface{}) {
	v, err := artifact.NewTypeInfoDepends(payloadDepends)
	if err != nil {
		panic("invalid type info depends")
	}
	d.args.TypeInfoV3.ArtifactDepends = v
}

func calculatePayloadChecksum(payload string) (string, error) {
	checksum := artifact.NewWriterChecksum(io.Discard)
	image, err := os.Open(payload)
	if err != nil {
		return "", err
	}
	defer image.Close()

	if _, err = io.Copy(checksum, image); err != nil {
		return "", err
	}

	return string(checksum.Checksum()), nil
}

// This clones the provides/depends/artifact_name/device_type values
// from the specified artifact into the writer.
func (d *ArtifactWriter) cloneMetaFromArtifact(artifact string) error {
	f, err := os.Open(artifact)
	if err != nil {
		return err
	}
	defer f.Close()

	reader := areader.NewReader(f)
	err = reader.ReadArtifactHeaders()
	if err != nil {
		return err
	}

	d.WithArtifactProvides(reader.GetArtifactProvides().ArtifactName, reader.GetArtifactProvides().ArtifactGroup)
	d.WithArtifactDepends(reader.GetArtifactDepends().ArtifactName, reader.GetArtifactDepends().CompatibleDevices, reader.GetArtifactDepends().ArtifactGroup)

	payloadProvides := map[string]string{}
	payloadDepends := map[string]interface{}{}
	for _, handler := range reader.GetHandlers() {
		provides, err := handler.GetUpdateProvides()
		if err != nil {
			return err
		}

		deps, err := handler.GetUpdateDepends()
		if err != nil {
			return err
		}

		for k, v := range provides {
			payloadProvides[k] = v
		}
		for k, v := range deps {
			payloadDepends[k] = v
		}
	}
	d.WithPayloadProvides(payloadProvides)
	d.withPayloadDependsTypeErased(payloadDepends)
	d.WithPayloadClearsProvides(reader.MergeArtifactClearsProvides())

	return nil
}

// Read provides from the first payload in the specified artifact
func readArtifactPayloadProvides(artifact string) (map[string]string, error) {
	f, err := os.Open(artifact)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	reader := areader.NewReader(f)
	err = reader.ReadArtifactHeaders()
	if err != nil {
		return nil, err
	}

	for _, handler := range reader.GetHandlers() {
		provides, err := handler.GetUpdateProvides()
		if err != nil {
			return nil, err
		}
		return provides, nil
	}
	return nil, errors.New("artifact does not contain a payload")
}

// Below, "Updates" is equivalent to "payload"
// The "composer" is responsible for adding files that are relevant to a certain update type
// Only support two for now - full rootfs image and delta rootfs image payloads
func (d *ArtifactWriter) WithFullRootfsPayload(pathToRootfs string) error {
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
