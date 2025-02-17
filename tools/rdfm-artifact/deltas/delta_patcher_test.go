package deltas

import (
	"os"
	"testing"
	
	"github.com/antmicro/rdfm/tools/rdfm-artifact/delta_engine"
	"github.com/stretchr/testify/assert"
)

const (
	testDeltaBaseArtifact   = "../tests/data/delta-base.rdfm"
	testDeltaTargetArtifact = "../tests/data/delta-target.rdfm"
)

func testDeltaPatcher(t *testing.T, deltaAlgoStr string, minSize int64) {
	deltaEngine, err := delta_engine.ParseDeltaEngine(deltaAlgoStr)
	patcher := NewArtifactDelta(testDeltaBaseArtifact, testDeltaTargetArtifact, deltaEngine)
	path, err := patcher.Delta()
	assert.Nil(t, err)
	defer os.Remove(path)

	info, err := os.Stat(path)
	assert.Nil(t, err)
	// Ensure the delta file is larger than the minimal size for non-identical files
	assert.Greater(t, info.Size(), minSize)
}

func TestRsyncDeltaPatcher(t *testing.T) {
	testDeltaPatcher(t, "rsync", 11)
}

func TestXdeltaPatcher(t *testing.T) {
	testDeltaPatcher(t, "xdelta", 62)
}
