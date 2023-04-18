package updaters

import (
	"errors"
	"io"
	"os"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/handlers"
)

// Custom UpdateStore for extracting files from artifacts
// This is required in order to extract the update files (i.e, the rootfs image)
// from an artifact using the `areader`, for the purposes of calculating the delta patch
// between a base and target artifacts.
// This supports only extracting a single file! Multi-file updates are not supported.
type UpdateFileStorer struct {
	FileContentReader *io.PipeReader
	fileContentWriter *io.PipeWriter
}

func NewUpdateFileStorer() UpdateFileStorer {
	r, w := io.Pipe()
	return UpdateFileStorer{
		FileContentReader: r,
		fileContentWriter: w,
	}
}

func (m *UpdateFileStorer) Initialize(artifactHeaders, artifactAugmentedHeaders artifact.HeaderInfoer, payloadHeaders handlers.ArtifactUpdateHeaders) error {
	// not required
	return nil
}

func (m UpdateFileStorer) PrepareStoreUpdate() error {
	// not required
	return nil
}

func (m *UpdateFileStorer) StoreUpdate(r io.Reader, info os.FileInfo) error {
	// Extract the file contents into a pipe
	n, err := io.CopyN(m.fileContentWriter, r, info.Size())

	//  I/O errors and EOF
	if err != nil && int64(n) != info.Size() {
		m.fileContentWriter.CloseWithError(err)
		return err
	}
	//  Incomplete reads?
	if int64(n) != info.Size() {
		err = errors.New("did not read entire file")
		m.fileContentWriter.CloseWithError(err)
		return err
	}

	m.fileContentWriter.Close()
	return nil
}

func (m UpdateFileStorer) FinishStoreUpdate() error {
	// not required
	return nil
}

// Required factory object for calling `SetUpdateStorerProducer` method on installer handlers
type UpdateFileStorerFactory struct {
	storer *UpdateFileStorer
}

func NewUpdateFileStorerFactory(storer *UpdateFileStorer) UpdateFileStorerFactory {
	return UpdateFileStorerFactory{
		storer: storer,
	}
}

func (f UpdateFileStorerFactory) NewUpdateStorer(updateType *string, payloadNum int) (handlers.UpdateStorer, error) {
	return f.storer, nil
}
