package cli

import (
	"fmt"
	"os"
	"path/filepath"

	log "github.com/sirupsen/logrus"

	"github.com/antmicro/rdfm-artifact/writers"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"

	"github.com/urfave/cli"
)

const (
	tempDirectory           = "rdfm-artifact-temp"
	destDirFilename         = "dest_dir"
	filenameFilename        = "filename"
	permissionsFilename     = "permissions"
	rollbackSupportFilename = "rollback_support"
)

func makeSingleFileFlags() []cli.Flag {
	return append(makeCommonArtifactModificationFlags(),
		cli.StringFlag{
			Name:     flagArtifactName,
			Usage:    "Name of the artifact",
			Required: true,
		},
		cli.StringSliceFlag{
			Name:     flagDeviceType,
			Usage:    "Device type this artifact is compatible with. Can be provided multiple times",
			Required: true,
		},
		cli.StringFlag{
			Name:     flagInputFilePath,
			Usage:    "Path to the input file.",
			Required: true,
		},
		cli.StringFlag{
			Name:     "dest-dir",
			Usage:    "The path on the device, where 'filename' is uploaded",
			Required: true,
		},
		cli.BoolFlag{
			Name:  "rollback-support",
			Usage: "Determines whether to create a backup of the file before updating",
		},
	)
}

func parseInputFileName(c *cli.Context) string {
	return filepath.Base(parseInputFile(c))
}

func parseDestDir(c *cli.Context) string {
	return c.String("dest-dir")
}

func parsePermissions(c *cli.Context) string {
	info, err := os.Stat(parseInputFile(c))
	if err != nil {
		log.Warnf("Failed to get file permissions: %s", err.Error())
		return "0644"
	}
	filePerm := info.Mode().Perm()
	log.Printf("Obtained file permissions: %o", filePerm)
	return fmt.Sprintf("%o", filePerm)
}

func parseRollbackSupport(c *cli.Context) string {
	rollback_value := "false"
	if c.Bool("rollback-support") {
		rollback_value = "true"
	}
	return rollback_value
}

func writeSingleFile(c *cli.Context) error {
	inputSingleFile := parseInputFile(c)

	// Obtaining the filename from the input path
	inputSingleFileName := parseInputFileName(c)

	filename_to_parse := map[string]string{
		destDirFilename:         parseDestDir(c),
		filenameFilename:        inputSingleFileName,
		permissionsFilename:     parsePermissions(c),
		rollbackSupportFilename: parseRollbackSupport(c),
	}

	// Checking if the input filename is one of reserved names
	_, present := filename_to_parse[inputSingleFileName]
	if present {
		return fmt.Errorf(
			"input filename '%s' is a reserved name. List of reserved names: %v",
			inputSingleFileName,
			[]string{destDirFilename, filenameFilename, permissionsFilename, rollbackSupportFilename},
		)
	}

	outputPath := parseOutputPath(c)
	payloadProvides, err := parsePayloadProvides(c)
	if err != nil {
		return err
	}
	payloadDepends, err := parsePayloadDepends(c)
	if err != nil {
		return err
	}
	payloadClearsProvides := parsePayloadClearsProvides(c)
	artifactName, artifactGroup := parseArtifactName(c), parseArtifactGroup(c)
	compatArtifacts, compatDevices, compatGroups := parseArtifactCompatibleArtifacts(c), parseArtifactCompatibleDevices(c), parseArtifactCompatibleGroups(c)

	handler := handlers.NewModuleImage("single-file")

	// Creating temporary files that are expected by artifact writer
	dir, er := os.MkdirTemp("", tempDirectory)
	defer os.RemoveAll(dir)

	if er != nil {
		return er
	}

	dataFiles := make([](*handlers.DataFile), 0, 5)

	// Creating metadata files and appending them to the artifact
	for _, file := range []string{destDirFilename, filenameFilename, permissionsFilename, rollbackSupportFilename} {
		targetFile := dir + "/" + file
		log.Println("Creating temporary file: ", targetFile)

		createdFile, er := os.Create(targetFile)
		if er != nil {
			return er
		}

		_, er = createdFile.WriteString(filename_to_parse[file] + "\n")
		if er != nil {
			return er
		}

		dataFiles = append(dataFiles, &handlers.DataFile{Name: createdFile.Name()})
	}

	// Appending the single file
	dataFiles = append(dataFiles, &handlers.DataFile{Name: inputSingleFile})
	handler.SetUpdateFiles(dataFiles)

	upd := &awriter.Updates{Updates: []handlers.Composer{handler}}

	writer := writers.NewSingleFileArtifactWriter(outputPath, upd)
	writer.WithArtifactProvides(artifactName, artifactGroup)
	writer.WithArtifactDepends(compatArtifacts, compatDevices, compatGroups)
	writer.WithPayloadProvides(payloadProvides)
	writer.WithPayloadDepends(payloadDepends)
	writer.WithPayloadClearsProvides(payloadClearsProvides)

	log.Info("Writing single file artifact...")
	return writer.Write()
}
