package cli

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

const (
	testArtifactName = "../tests/data/dummy-artifact.rdfm"
)

func TestReadArtifact(t *testing.T) {
	if _, err := os.Stat(testArtifactName); err != nil {
		t.Skipf("Test artifact %s does not exist - skipping!", testArtifactName)
	}

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"read",
		testArtifactName,
	})
	assert.Nil(t, err)
}
