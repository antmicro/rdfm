package writers

import (
	"errors"
	"io"
	"os"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
)

// This is a simple wrapper for awriter for easier manipulation of artifact metadata
type ArtifactWriter struct {
	pathToDeltas string
	outputPath   string
	args         awriter.WriteArtifactArgs
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
