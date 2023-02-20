package cli

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

const (
	testArtifactName = "testArtifact.rdfm"
)

// This tests whether unknown subcommands are passed through properly to mender-artifact
// This should return a success status (mender-artifact was called successfully)
func TestMenderArtifactPassthrough(t *testing.T) {
	if _, err := os.Stat(testArtifactName); err != nil {
		t.Skipf("Test artifact %s does not exist - skipping!", testArtifactName)
	}

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"dump",
		testArtifactName,
	})
	assert.Nil(t, err)
}
