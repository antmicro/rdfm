package updaters_test

import (
	"io"
	"os"
	"sync"
	"testing"

	"github.com/antmicro/rdfm-artifact/updaters"
	"github.com/stretchr/testify/assert"
)

const (
	testArtifactPath            = "../tests/data/dummy-artifact.rdfm"
	testArtifactRootfsImageSize = 1048576
)

// This tests the rootfs image extractor helper
func TestArtifactExtractor(t *testing.T) {

	extractor := updaters.NewArtifactExtractor()
	err := extractor.Open(testArtifactPath)
	assert.Nil(t, err)
	defer extractor.Close()

	var g sync.WaitGroup
	g.Add(2)

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
		written, err := io.Copy(out, extractor.Reader())
		assert.Nil(t, err)
		// Checking the length is good enough
		assert.Equal(t, written, int64(testArtifactRootfsImageSize))
	}()

	// The artifact reader writes the rootfs image to the pipe in UpdateFileStorer during the ReadArtifactData call
	err = extractor.Extract()
	assert.Nil(t, err)
}
