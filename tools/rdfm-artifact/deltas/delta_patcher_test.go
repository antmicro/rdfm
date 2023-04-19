package deltas

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestDeltaPatcher(t *testing.T) {
	patcher := NewArtifactDelta("../tests/data/delta-base.rdfm", "../tests/data/delta-target.rdfm")
	path, err := patcher.Delta()
	assert.Nil(t, err)

	info, err := os.Stat(path)
	assert.Nil(t, err)
	// Taking the delta of two identical files using librsync outputs an 11-byte delta
	// We expect the delta to be larger than this when the files differ
	assert.Greater(t, info.Size(), int64(11))
}
