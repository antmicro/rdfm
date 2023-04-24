package cli

import (
	"os"
	"testing"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/stretchr/testify/assert"
)

const (
	// Relative to the cli/ directory
	testRootfsPayload      = "../tests/data/dummy-rootfs.img"
	testRootfsArtifactPath = "../tests/data/full-rootfs-test.rdfm"
)

// Test writing a full rootfs artifact, along with its metadata
func TestWriteFullRootfsArtifact(t *testing.T) {
	defer os.Remove(testRootfsArtifactPath)

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"rootfs-image",
		"--artifact-name", "dummy_name",
		"--device-type", "dummy_type",
		"--device-type", "different_dummy_type", // Also test if passing multiple values works properly
		"--depends-artifacts", "depended_artifact",
		"--depends-artifacts", "another_depended_artifact",
		"--depends-groups", "depended_group",
		"--depends-groups", "another_depended_group",
		"--provides-group", "provided_group",
		"--clears-provides", "cleared_provide",
		"--clears-provides", "another_cleared_provide",
		"--provides", "provide1:AAAAAAAAAAAA",
		"--provides", "provide2:BBBBBBBBBBBB",
		"--depends", "depend1:11111111",
		"--depends", "depend2:22222222",
		"--output-path", testRootfsArtifactPath,
		testRootfsPayload,
	})
	assert.Nil(t, err)

	f, err := os.Open(testRootfsArtifactPath)
	assert.Nil(t, err)
	defer f.Close()

	// Verify whether the artifact looks sane
	reader := areader.NewReader(f)
	assert.Nil(t, reader.ReadArtifact())
	assert.Equal(t, 3, reader.GetInfo().Version)
	assert.Equal(t, "dummy_name", reader.GetArtifactName())
	assert.Equal(t, []string{"dummy_type", "different_dummy_type"}, reader.GetCompatibleDevices())
	assert.Equal(t, []string{"depended_artifact", "another_depended_artifact"}, reader.GetArtifactDepends().ArtifactName)
	assert.Equal(t, []string{"depended_group", "another_depended_group"}, reader.GetArtifactDepends().ArtifactGroup)
	assert.Equal(t, "provided_group", reader.GetArtifactProvides().ArtifactGroup)
	assert.Equal(t, "dummy_name", reader.GetArtifactProvides().ArtifactName)
	assert.Equal(t, []string{"cleared_provide", "another_cleared_provide"}, reader.MergeArtifactClearsProvides())

	// Merged provides also include the artifact name and group, alongside user-provided values.
	provides, err := reader.MergeArtifactProvides()
	assert.Nil(t, err)
	assert.Equal(t, map[string]string{
		"artifact_group": "provided_group",
		"artifact_name":  "dummy_name",
		"provide1":       "AAAAAAAAAAAA",
		"provide2":       "BBBBBBBBBBBB",
	}, provides)

	// Merged depends include all of the dependency values, including device type, artifact name,
	// group, and the user-specified custom depends values for the artifact.
	depends, err := reader.MergeArtifactDepends()
	assert.Nil(t, err)
	// The artifact library uses map to interface{} for type erasure, which is why
	// this is a bit messy..
	assert.Equal(t, map[string]interface{}(map[string]interface{}{
		"artifact_group": []interface{}{"depended_group", "another_depended_group"},
		"artifact_name":  []interface{}{"depended_artifact", "another_depended_artifact"},
		"depend1":        "11111111",
		"depend2":        "22222222",
		"device_type":    []interface{}{"dummy_type", "different_dummy_type"},
	}), depends)
}
