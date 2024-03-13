package cli

import (
	"os"
	"testing"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/stretchr/testify/assert"
)

const (
	// Relative to the cli/ directory
	testGroupInvalidTarget = "invalid:../tests/data/dummy-zephyr-group.invalid.img"
	testGroupTargetOne     = "one:../tests/data/dummy-zephyr.img"
	testGroupTargetTwo     = "two:../tests/data/dummy-zephyr-group.img"
	testGroupArtifactPath  = "../tests/data/group-test.rdfm"
	testGroupVersion       = "0.1.2+3"
)

// Test writing group artifact with targets with mismatched image versions
func TestWriteGroupWithMismatchVersion(t *testing.T) {
	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"zephyr-group-image",
		"--group-type", "dummy_type",
		"--target", testGroupTargetOne,
		"--target", testGroupInvalidTarget,
	})

	assert.ErrorContains(t, err, "Version mismatch between images")
}

func TestWriteGroupArtifact(t *testing.T) {
	defer os.Remove(testGroupArtifactPath)

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"zephyr-group-image",
		"--group-type", "dummy-type",
		"--provides", "provide:foo",
		"--output-path", testGroupArtifactPath,
		"--target", testGroupTargetOne,
		"--target", testGroupTargetTwo,
	})

	assert.Nil(t, err)

	f, err := os.Open(testGroupArtifactPath)
	assert.Nil(t, err)
	defer f.Close()

	reader := areader.NewReader(f)
	assert.Nil(t, reader.ReadArtifact())

	assert.Equal(t, 3, reader.GetInfo().Version)
	assert.Equal(t, 1, len(reader.GetUpdates()))
	assert.Equal(t, "zephyr-group-image", *reader.GetUpdates()[0].Type)
	assert.Equal(t, []string{"dummy-type"}, reader.GetCompatibleDevices())
	assert.Equal(t, testGroupVersion, reader.GetArtifactProvides().ArtifactName)

	provides, err := reader.MergeArtifactProvides()
	assert.Nil(t, err)
	assert.Equal(t, map[string]string{
		"artifact_name":                 testGroupVersion,
		"provide":                       "foo",
		"zephyr-group-image.target.one": "c80255d84ba460b36da8974a7587665c5dfde62ba7d7ad2669c91e75263f651f",
		"zephyr-group-image.target.two": "8babae5135c204f35ca8397f8bfffcef8e06f25d727fa4a8e26734a0382e4c70",
		"zephyr-group-image.version":    testGroupVersion,
	}, provides)

	inst := reader.GetHandlers()
	assert.Equal(t, 1, len(inst))

	files := inst[0].GetUpdateFiles()
	assert.Equal(t, 2, len(files))

	for i, tt := range []struct {
		name, checksum string
	}{
		{"one", "c80255d84ba460b36da8974a7587665c5dfde62ba7d7ad2669c91e75263f651f"},
		{"two", "8babae5135c204f35ca8397f8bfffcef8e06f25d727fa4a8e26734a0382e4c70"},
	} {
		assert.Equal(t, files[i].Name, tt.name)
		assert.Equal(t, string(files[i].Checksum), tt.checksum)
	}
}
