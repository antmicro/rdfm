package writers

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"path"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"
)

type GroupArtifactWriter struct {
	ArtifactWriter
}

func NewGroupArtifactWriter(outputPath string) GroupArtifactWriter {
	return GroupArtifactWriter{
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

func (w *GroupArtifactWriter) WithGroupPayload(devFileMap map[string]string, targetVersion string) error {
	w.setProvidesVersion(targetVersion)

	tmpDir, err := os.MkdirTemp("", "rdfm-group")
	if err != nil {
		return err
	}

	updateFiles := make([]*handlers.DataFile, 0, len(devFileMap))
	for dev, file := range devFileMap {
		file, handle, err := makeUnique(file, path.Join(tmpDir, dev))
		if err != nil {
			return err
		}
		defer handle.Close()

		// Validate image
		if err := validateImageMagic(handle); err != nil {
			return err
		}

		imgVersion, err := imgVersion(handle)
		if err != nil {
			return err
		}
		if imgVersion != targetVersion {
			return fmt.Errorf("Version mismatch between images (target version is %s, while '%s' has %s)", targetVersion, file, imgVersion)
		}

		checksum, err := imgChecksum(handle)
		if err != nil {
			return err
		}
		w.args.TypeInfoV3.ArtifactProvides[fmt.Sprintf("%s.%s", rdfmGroupProvidesTarget, dev)] = fmt.Sprintf("%x", checksum)

		updateFiles = append(updateFiles, &handlers.DataFile{Name: file, Checksum: checksum})
	}

	moduleHandler := handlers.NewModuleImage("zephyr-group-image")
	if err := moduleHandler.SetUpdateFiles(updateFiles); err != nil {
		return err
	}

	w.args.Updates.Updates = []handlers.Composer{moduleHandler}

	return nil
}

func (w *GroupArtifactWriter) setProvidesVersion(version string) {
	if w.args.TypeInfoV3.ArtifactProvides == nil {
		w.WithPayloadProvides(map[string]string{
			rdfmGroupProvidesVersion: version,
		})
	} else {
		w.args.TypeInfoV3.ArtifactProvides[rdfmGroupProvidesVersion] = version
	}
}

func imgVersion(image io.ReadSeeker) (string, error) {
	// https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/mcuboot/design.html#image-format
	// Image version is embedded in image header at 20 bytes offset
	if _, err := image.Seek(20, 0); err != nil {
		return "", err
	}

	var major, minor uint8
	var revision uint16
	var buildNum uint32

	if err := binary.Read(image, binary.LittleEndian, &major); err != nil {
		return "", err
	}
	if err := binary.Read(image, binary.LittleEndian, &minor); err != nil {
		return "", err
	}
	if err := binary.Read(image, binary.LittleEndian, &revision); err != nil {
		return "", err
	}
	if err := binary.Read(image, binary.LittleEndian, &buildNum); err != nil {
		return "", err
	}

	if buildNum == 0 {
		return fmt.Sprintf("%d.%d.%d", major, minor, revision), nil
	}

	return fmt.Sprintf("%d.%d.%d+%d", major, minor, revision, buildNum), nil
}

func imgChecksum(image io.ReadSeeker) ([]byte, error) {
	if _, err := image.Seek(0, 0); err != nil {
		return nil, err
	}

	h := sha256.New()
	if _, err := io.Copy(h, image); err != nil {
		return nil, err
	}

	return h.Sum(nil), nil
}

func makeUnique(src, dst string) (string, *os.File, error) {
	srcHandle, err := os.Open(src)
	if err != nil {
		return "", nil, err
	}
	defer srcHandle.Close()

	dstHandle, err := os.Create(dst)
	if err != nil {
		return "", nil, err
	}

	if _, err := io.Copy(dstHandle, srcHandle); err != nil {
		return "", nil, err
	}

	return dst, dstHandle, nil
}
