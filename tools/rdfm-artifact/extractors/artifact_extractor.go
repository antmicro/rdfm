package extractors

import (
	"io"
	"os"

	"github.com/mendersoftware/mender-artifact/areader"
)

type ArtifactRootfsReader struct {
	storer   UpdateFileStorer
	reader   *areader.Reader
	artifact *os.File
}

func NewArtifactExtractor() ArtifactRootfsReader {
	return ArtifactRootfsReader{
		storer: NewUpdateFileStorer(),
	}
}

// Returns a reader for the contents of the rootfs image contained in the artifact
func (e *ArtifactRootfsReader) Reader() *io.PipeReader {
	return e.storer.FileContentReader
}

// Returns the file size of the extracted rootfs image
func (e *ArtifactRootfsReader) PayloadSize() int64 {
	return e.storer.FileSize
}

// Open an artifact for extraction
func (e *ArtifactRootfsReader) Open(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}

	// Set up the artifact reader for dumping the rootfs image
	reader := areader.NewReader(f)
	err = reader.ReadArtifactHeaders()
	if err != nil {
		f.Close()
		return err
	}

	// Set up the update storer so that it's called for every single update type
	// an artifact can contain.
	for _, v := range reader.GetHandlers() {
		v.SetUpdateStorerProducer(NewUpdateFileStorerFactory(&e.storer))
	}
	e.reader = reader
	e.artifact = f

	return nil
}

// Extract the contents of the artifact
// You MUST call Extract() from a different goroutine than the one reading
// rootfs data using the Reader().
func (e *ArtifactRootfsReader) Extract() error {
	return e.reader.ReadArtifactData()
}

// Close the artifact file
func (e *ArtifactRootfsReader) Close() error {
	return e.artifact.Close()
}
