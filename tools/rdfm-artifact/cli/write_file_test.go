package cli

import (
	"fmt"
	"os"
	"testing"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/mendersoftware/mender-artifact/handlers"
	"github.com/stretchr/testify/assert"
)

const (
	// Relative to the cli/ directory
	testFilePayload       = "../tests/data/dummy-single-file.bin"
	testFileArtifactPath  = "../tests/data/single-file-test.rdfm"
	invalidFilesDirectory = "../tests/data/invalid_single_file"
)

func TestWriteSingleFileConflictingName(t *testing.T) {
	app := NewApp()

	for _, filename := range []string{destDirFilename, filenameFilename, permissionsFilename, rollbackSupportFilename} {
		err := app.Run([]string{
			"rdfm-artifact",
			"write",
			"single-file",
			"--artifact-name", "dummy_name",
			"--device-type", "dummy_type",
			"--file", invalidFilesDirectory + "/" + filename,
			"--dest-dir", "/dummy/dir",
		})

		assert.ErrorContains(t, err, fmt.Sprintf("input filename '%v' is a reserved name.", filename))
	}
}

func TestWriteSingleFileNonexistentSourceFile(t *testing.T) {
	app := NewApp()

	filename := "somefilethatdoesnotexist"
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"single-file",
		"--artifact-name", "dummy_name",
		"--device-type", "dummy_type",
		"--file", filename,
		"--dest-dir", "/dummy/dir",
	})

	assert.ErrorContains(t, err, fmt.Sprintf("can not open data file: %v", filename))
}

// Test writing a single file artifact, along with its metadata
func TestWriteSingleFileArtifact(t *testing.T) {
	defer os.Remove(testFileArtifactPath)

	app := NewApp()
	err := app.Run([]string{
		"rdfm-artifact",
		"write",
		"single-file",
		"--artifact-name", "dummy_name",
		"--device-type", "dummy_type",
		"--output-path", testFileArtifactPath,
		"--file", testFilePayload,
		"--dest-dir", "/dummy/dir",
		"--rollback-support",
	})
	assert.Nil(t, err)

	f, err := os.Open(testFileArtifactPath)
	assert.Nil(t, err)
	defer f.Close()

	// Verify whether the artifact looks sane
	reader := areader.NewReader(f)
	assert.Nil(t, reader.ReadArtifact())
	assert.Equal(t, 3, reader.GetInfo().Version)
	assert.Equal(t, "dummy_name", reader.GetArtifactName())
	assert.Equal(t, []string{"dummy_type"}, reader.GetCompatibleDevices())

	assert.Equal(t, *reader.GetUpdates()[0].Type, "single-file")

	// Merged provides also include the artifact name and group, alongside user-provided values.
	provides, err := reader.MergeArtifactProvides()
	assert.Nil(t, err)
	assert.Equal(t, map[string]string{
		"artifact_name": "dummy_name",
	}, provides)

	inst := reader.GetHandlers()
	assert.Equal(t, 1, len(inst))

	// Files length, names and hashes verification.
	allFiles := reader.GetHandlers()[0].GetUpdateAllFiles()
	assert.Equal(t, 5, len(allFiles))

	dest_dir_datafile := handlers.DataFile{
		Name:     "dest_dir",
		Size:     11,               // /dummy/dir + newline makes 11 characters
		Date:     allFiles[0].Date, // Date depends on the system, so we can't compare it directly
		Checksum: []byte("bd9246501126e422a428727bb18dea41a6a9f2684fd6eaf0cbaebcd246abefcf"),
	}

	filename_datafile := handlers.DataFile{
		Name:     "filename",
		Size:     22,               // dummy-single-file.bin + newline makes 22 characters
		Date:     allFiles[1].Date, // Date depends on the system, so we can't compare it directly
		Checksum: []byte("f12e432a6b267fb147cf7875651f3ebd6f77f15631a275ee761befaac2b85cbd"),
	}

	permissions_datafile := handlers.DataFile{
		Name:     "permissions",
		Size:     4,                // 644 + newline makes 4 characters
		Date:     allFiles[2].Date, // Date depends on the system, so we can't compare it directly
		Checksum: []byte("0a2a5ea75282bf45dfcd2df50bea57b953ffecba63d8809c4e9abd233b828f73"),
	}

	rollback_datafile := handlers.DataFile{
		Name:     "rollback_support",
		Size:     5,                // true + newline makes 5 characters
		Date:     allFiles[3].Date, // Date depends on the system, so we can't compare it directly
		Checksum: []byte("a17fcf0a2f50e2d495e4f90ce263410edc183add6c62699a2facbccf60410f74"),
	}

	file_datafile := handlers.DataFile{
		Name:     "dummy-single-file.bin",
		Size:     1048576,          // true + newline makes 5 characters
		Date:     allFiles[4].Date, // Date depends on the system, so we can't compare it directly
		Checksum: []byte("3708af0710d137931f057d78b2cd53c572f04bacbc69ff18b79fd20aaf464373"),
	}

	assert.Equal(t, dest_dir_datafile, *allFiles[0])
	assert.Equal(t, filename_datafile, *allFiles[1])
	assert.Equal(t, permissions_datafile, *allFiles[2])
	assert.Equal(t, rollback_datafile, *allFiles[3])
	assert.Equal(t, file_datafile, *allFiles[4])
}
