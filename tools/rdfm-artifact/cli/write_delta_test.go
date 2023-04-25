package cli

import (
	"os"
	"testing"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/stretchr/testify/assert"
)

const (
	testDeltaRootfsBase   = "../tests/data/delta-base.rdfm"
	testDeltaRootfsTarget = "../tests/data/delta-target.rdfm"
	testDeltaRootfsOut    = "../tests/data/delta-output-test.rdfm"
)

func TestWriteDeltaRootfsArtifact(t *testing.T) {
	defer os.Remove(testDeltaRootfsOut)

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"delta-rootfs-image",
		"--base-artifact", testDeltaRootfsBase,
		"--target-artifact", testDeltaRootfsTarget,
		"--output-path", testDeltaRootfsOut,
	})
	assert.Nil(t, err)

	f, err := os.Open(testDeltaRootfsOut)
	assert.Nil(t, err)
	defer f.Close()

	reader := areader.NewReader(f)
	assert.Nil(t, reader.ReadArtifactHeaders())

	// rootfs-image.checksum value provided by the delta must match the checksum of the
	// updated rootfs image (dummy-update-rootfs.img), as this is the result of applying
	// the deltas on top of the base
	provides, err := reader.MergeArtifactProvides()
	assert.Nil(t, err)
	assert.Equal(t, map[string]string{
		"AAAAAAAA":              "11111111",
		"artifact_name":         "delta-target",
		"rootfs-image.checksum": "6e0632c415f8bcee4a113917f515c080a9a991ae02f044d8e1fdf0bc47c0a62d",
		"rootfs-image.version":  "delta-target",
	}, provides)

	// rootfs-image.checksum value depended on by the delta must match the checksum of the
	// base rootfs image (dummy-rootfs.img), so we don't try to apply deltas on top of an
	// invalid base image
	depends, err := reader.MergeArtifactDepends()
	assert.Nil(t, err)
	assert.Equal(t, map[string]interface{}{
		"BBBBBBBB":              "22222222",
		"device_type":           []interface{}{"some-device-type"},
		"rootfs-image.checksum": "f0f37130db8accd0ef87b03dc65a3e085b15a90185100589038e4eb98e452ba7",
	}, depends)
}
