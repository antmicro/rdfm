package cli

import (
	"os"
	"testing"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/stretchr/testify/assert"
)

const (
	// Relative to the cli/ directory
	testZephyrPayload         = "../tests/data/dummy-zephyr.img"
	testZephyrInvalidPayload  = "../tests/data/dummy-zephyr.invalid.img"
	testZephyrArtifactPath    = "../tests/data/zephyr-test.rdfm"
	testZephyrArtifactVersion = "0.1.2+3"
)

// Test writing a full rootfs artifact, along with its metadata
func TestWriteInvalidZephyrArtifact(t *testing.T) {
	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"zephyr-image",
		"--device-type", "dummy_type",
		"--device-type", "different_dummy_type", // Also test if passing multiple values works properly
		"--artifact-name-depends", "depended_artifact",
		"--artifact-name-depends", "another_depended_artifact",
		"--depends-groups", "depended_group",
		"--depends-groups", "another_depended_group",
		"--provides-group", "provided_group",
		"--clears-provides", "cleared_provide",
		"--clears-provides", "another_cleared_provide",
		"--provides", "provide1:AAAAAAAAAAAA",
		"--provides", "provide2:BBBBBBBBBBBB",
		"--depends", "depend1:11111111",
		"--depends", "depend2:22222222",
		"--output-path", testZephyrArtifactPath,
		"--file", testZephyrInvalidPayload,
	})

	assert.ErrorContains(t, err, "incorrect magic value")
}

func TestWriteZephyrArtifactInvalidArgs(t *testing.T) {
	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"zephyr-image",
		"--device-type", "dummy_type",
		"--device-type", "different_dummy_type", // Also test if passing multiple values works properly
		"--artifact-name-depends", "depended_artifact",
		"--artifact-name-depends", "another_depended_artifact",
		"--depends-groups", "depended_group",
		"--depends-groups", "another_depended_group",
		"--provides-group", "provided_group",
		"--clears-provides", "cleared_provide",
		"--clears-provides", "another_cleared_provide",
		"--provides", "provide1:AAAAAAAAAAAA",
		"--provides", "provide2:BBBBBBBBBBBB",
		"--depends", "depend1:11111111",
		"--depends", "depend2:22222222",
		"--output-path", testZephyrArtifactPath,
		"--file", testZephyrInvalidPayload,
		"positional",
	})

	assert.ErrorContains(t, err, "zephyr-image: unexpected positional arguments: [positional]")
}

func TestWriteZephyrArtifact(t *testing.T) {
	defer os.Remove(testZephyrArtifactPath)

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"zephyr-image",
		"--device-type", "dummy_type",
		"--device-type", "different_dummy_type", // Also test if passing multiple values works properly
		"--artifact-name-depends", "depended_artifact",
		"--artifact-name-depends", "another_depended_artifact",
		"--depends-groups", "depended_group",
		"--depends-groups", "another_depended_group",
		"--provides-group", "provided_group",
		"--clears-provides", "cleared_provide",
		"--clears-provides", "another_cleared_provide",
		"--provides", "provide1:AAAAAAAAAAAA",
		"--provides", "provide2:BBBBBBBBBBBB",
		"--depends", "depend1:11111111",
		"--depends", "depend2:22222222",
		"--output-path", testZephyrArtifactPath,
		"--file", testZephyrPayload,
	})
	assert.Nil(t, err)

	f, err := os.Open(testZephyrArtifactPath)
	assert.Nil(t, err)
	defer f.Close()

	// Verify whether the artifact looks sane
	reader := areader.NewReader(f)
	assert.Nil(t, reader.ReadArtifact())
	assert.Equal(t, 3, reader.GetInfo().Version)
	assert.Equal(t, "zephyr-image", *reader.GetUpdates()[0].Type)
	assert.Equal(t, testZephyrArtifactVersion, reader.GetArtifactName())
	assert.Equal(t, []string{"dummy_type", "different_dummy_type"}, reader.GetCompatibleDevices())
	assert.Equal(t, []string{"depended_artifact", "another_depended_artifact"}, reader.GetArtifactDepends().ArtifactName)
	assert.Equal(t, []string{"depended_group", "another_depended_group"}, reader.GetArtifactDepends().ArtifactGroup)
	assert.Equal(t, "provided_group", reader.GetArtifactProvides().ArtifactGroup)
	assert.Equal(t, testZephyrArtifactVersion, reader.GetArtifactProvides().ArtifactName)
	assert.Equal(t, []string{"cleared_provide", "another_cleared_provide"}, reader.MergeArtifactClearsProvides())
}
