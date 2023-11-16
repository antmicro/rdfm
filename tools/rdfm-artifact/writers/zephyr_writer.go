package writers

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"os"
	"path"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"
)

const (
	IMAGE_MAGIC  = 0x96f3b83d
	TARGET_IMAGE = "zephyr.signed.bin"
)

type ZephyrArtifactWriter struct {
	ArtifactWriter
}

func NewZephyrArtifactWriter(outputPath string) ZephyrArtifactWriter {
	return ZephyrArtifactWriter{
		ArtifactWriter{
			pathToDeltas: "",
			outputPath:   outputPath,
			args: awriter.WriteArtifactArgs{
				Format:     rdfmArtifactFormat,
				Version:    rdfmArtifactVersion,
				Updates:    &awriter.Updates{},
				TypeInfoV3: &artifact.TypeInfoV3{},
			},
		},
	}
}

func (d *ZephyrArtifactWriter) WithFullZephyrPayload(pathToImage, version string) error {
	if err := validateImageMagic(pathToImage); err != nil {
		return err
	}

	pathToImage, err := setupImageFile(pathToImage)
	if err != nil {
		return err
	}

	checksum, err := calculatePayloadChecksum(pathToImage)
	if err != nil {
		return err
	}

	if d.args.TypeInfoV3.ArtifactProvides != nil {
		d.args.TypeInfoV3.ArtifactProvides[rdfmZephyrProvidesChecksum] = checksum
		d.args.TypeInfoV3.ArtifactProvides[rdfmZephyrProvidesVersion] = version
	} else {
		d.WithPayloadProvides(map[string]string{
			rdfmZephyrProvidesChecksum: checksum,
			rdfmZephyrProvidesVersion:  version,
		})
	}

	handler := handlers.NewModuleImage("zephyr-image")
	dataFiles := [](*handlers.DataFile){
		&handlers.DataFile{Name: pathToImage},
	}

	if err := handler.SetUpdateFiles(dataFiles); err != nil {
		return err
	}

	d.args.Updates.Updates = []handlers.Composer{
		handler,
	}
	return nil
}

func validateImageMagic(pathToImage string) error {
	file, err := os.Open(pathToImage)
	if err != nil {
		return err
	}
	defer file.Close()

	var val uint32
	if err := binary.Read(file, binary.LittleEndian, &val); err != nil {
		return err
	}

	if val != IMAGE_MAGIC {
		return errors.New(fmt.Sprintf("Bad image (incorrect magic value: expected 0x%x, found 0x%x)", IMAGE_MAGIC, val))
	}

	return nil
}

func setupImageFile(pathToImage string) (string, error) {
	// If the provided file is already named correctly,
	// we don't have to do anything with it
	if pathToImage == TARGET_IMAGE {
		return pathToImage, nil
	}

	inFile, err := os.Open(pathToImage)
	if err != nil {
		return pathToImage, err
	}
	defer inFile.Close()

	tmpDir, err := os.MkdirTemp("", "rdfm-artifact")
	if err != nil {
		return pathToImage, err
	}

	tmpFile := path.Join(tmpDir, TARGET_IMAGE)
	outFile, err := os.Create(tmpFile)
	if err != nil {
		return pathToImage, err
	}
	defer outFile.Close()

	if _, err := io.Copy(outFile, inFile); err != nil {
		return pathToImage, err
	}

	return tmpFile, nil
}
