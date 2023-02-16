package main

import (
	"os"
	"testing"

	"github.com/antmicro/rdfm-artifact/cli"
	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/stretchr/testify/assert"
)

// Test writing a full rootfs artifact, along with its metadata
func TestWriteFullRootfsArtifact(t *testing.T) {
	app := cli.NewApp()
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
		"update.img",
	})
	assert.Nil(t, err)

	f, err := os.Open("artifact.rdfm")
	assert.Nil(t, err)
	defer f.Close()

	// Verify whether the artifact looks sane
	reader := areader.NewReader(f)
	assert.Nil(t, reader.ReadArtifact())
	assert.Equal(t, reader.GetInfo().Version, 3)
	assert.Equal(t, reader.GetArtifactName(), "dummy_name")
	assert.Equal(t, reader.GetCompatibleDevices(), []string{"dummy_type", "different_dummy_type"})
	assert.Equal(t, reader.GetArtifactDepends().ArtifactName, []string{"depended_artifact", "another_depended_artifact"})
	assert.Equal(t, reader.GetArtifactDepends().ArtifactGroup, []string{"depended_group", "another_depended_group"})
	assert.Equal(t, reader.GetArtifactProvides().ArtifactGroup, "provided_group")
	assert.Equal(t, reader.GetArtifactProvides().ArtifactName, "dummy_name")
	assert.Equal(t, reader.MergeArtifactClearsProvides(), []string{"cleared_provide", "another_cleared_provide"})

	provides, err := reader.MergeArtifactProvides()
	assert.Nil(t, err)
	assert.Equal(t, provides, map[string]string{
		"provide1": "AAAAAAAAAAAA",
		"provide2": "BBBBBBBBBBBB",
	})

	depends, err := reader.MergeArtifactDepends()
	assert.Nil(t, err)
	assert.Equal(t, depends, map[string]string{
		"depend1": "11111111",
		"depend2": "22222222",
	})
}
