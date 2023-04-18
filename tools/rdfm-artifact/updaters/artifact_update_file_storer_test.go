package updaters_test

import (
	"io"
	"os"
	"sync"
	"testing"

	"github.com/antmicro/rdfm-artifact/updaters"
	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/stretchr/testify/assert"
)

const (
	testArtifactPath            = "../tests/data/testArtifact.rdfm"
	testArtifactRootfsImageSize = 1048576
)

// This tests the rootfs image extractor helper
func TestArtifactFileStorer(t *testing.T) {
	f, err := os.Open(testArtifactPath)
	assert.Nil(t, err)
	defer f.Close()

	storer := updaters.NewUpdateFileStorer()

	// Set up the artifact reader for dumping the rootfs image
	reader := areader.NewReader(f)
	err = reader.ReadArtifactHeaders()
	assert.Nil(t, err)
	for _, v := range reader.GetHandlers() {
		v.SetUpdateStorerProducer(updaters.NewUpdateFileStorerFactory(&storer))
	}

	var g sync.WaitGroup
	g.Add(2)

	// The artifact reader writes the rootfs image to the pipe in UpdateFileStorer during the ReadArtifactData call
	go func() {
		defer g.Done()

		err = reader.ReadArtifactData()
		assert.Nil(t, err)
	}()

	// This goroutine is a sink for the file contents from the artifact extractor
	// We just write the rootfs image to a temp file somewhere
	go func() {
		defer g.Done()

		out, err := os.CreateTemp(os.TempDir(), "rdfm-test-")
		assert.Nil(t, err)
		defer func() {
			name := out.Name()
			out.Close()
			os.Remove(name)
		}()

		// We just copy the file contents to a temp file here
		written, err := io.Copy(out, storer.FileContentReader)
		assert.Nil(t, err)
		// Checking the length is good enough
		assert.Equal(t, written, int64(testArtifactRootfsImageSize))
	}()
}
