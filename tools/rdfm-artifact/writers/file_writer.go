package writers

import (
	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
)

type SingleFileArtifactWriter struct {
	ArtifactWriter
}

func NewSingleFileArtifactWriter(outputPath string, updates *awriter.Updates) SingleFileArtifactWriter {
	return SingleFileArtifactWriter{
		ArtifactWriter{
			pathToDeltas: "", // This is unused for single-file updates for now
			outputPath:   outputPath,
			args: awriter.WriteArtifactArgs{
				Format:     rdfmArtifactFormat,
				Version:    rdfmArtifactVersion,
				Updates:    updates,
				TypeInfoV3: &artifact.TypeInfoV3{},
			},
		},
	}
}
