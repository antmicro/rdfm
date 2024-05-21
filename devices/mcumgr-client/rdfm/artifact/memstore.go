package artifact

import (
	"io"
	"os"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/handlers"
)

// Implements `UpdateStorer` interface to allow
// extracting individual update files to memory
type MemStore struct {
	UpdateType     string
	ExtractedFiles map[string][]byte
}

func (m *MemStore) Initialize(artHeaders, artAuthHeaders artifact.HeaderInfoer, payloadHeaders handlers.ArtifactUpdateHeaders) error {
	m.ExtractedFiles = make(map[string][]byte)
	return nil
}

func (m *MemStore) PrepareStoreUpdate() error {
	return nil
}

func (m *MemStore) StoreUpdate(r io.Reader, info os.FileInfo) error {
	buf := make([]byte, info.Size())
	if _, err := io.ReadFull(r, buf); err != nil {
		return err
	}

	m.ExtractedFiles[info.Name()] = buf
	return nil
}

func (m *MemStore) FinishStoreUpdate() error {
	return nil
}

type MemStoreFactory struct {
	*MemStore
}

// Convenience function to create new `MemStoreFactory`
// while also getting its underlying `MemStore`
func NewMemStoreFactory() (MemStoreFactory, *MemStore) {
	f := MemStoreFactory{
		&MemStore{},
	}
	return f, f.MemStore
}

// Util for setting `MemStore` as target & reading
// in the artifact
func ReadArtifactToMem(reader *areader.Reader) (*MemStore, error) {
	f, store := NewMemStoreFactory()

	for _, v := range reader.GetHandlers() {
		v.SetUpdateStorerProducer(f)
	}

	if err := reader.ReadArtifactData(); err != nil {
		return nil, err
	}

	return store, nil
}

// Needed to satisfy `UpdateStorerProducer` interface
// for setting our UpdateStorer when extracting artifact
// Each factory will always return a pointer to its
// underlying `MemStore`
func (f MemStoreFactory) NewUpdateStorer(updateType *string, payloadNum int) (handlers.UpdateStorer, error) {
	f.MemStore.UpdateType = *updateType
	return f.MemStore, nil
}
