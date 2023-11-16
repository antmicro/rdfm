package cli

import (
	"encoding/binary"
	"fmt"
	"log"
	"os"

	"github.com/antmicro/rdfm-artifact/writers"
	"github.com/urfave/cli"
)

func makeFullZephyrFlags() []cli.Flag {
	return append(makeCommonArtifactModificationFlags(),
		cli.StringSliceFlag{
			Name:     flagDeviceType,
			Usage:    "Device type this artifact is compatible with. Can be provided multiple times",
			Required: true,
		},
		cli.StringFlag{
			Name:     flagInputFilePath,
			Usage:    "Path to the Zephyr MCUboot `IMAGE`",
			Required: true,
		},
	)
}

func writeFullZephyr(c *cli.Context) error {
	inputZephyrImage := c.String(flagInputFilePath)
	outputPath := parseOutputPath(c)
	payloadProvides, err := parsePayloadProvides(c)
	if err != nil {
		return err
	}

	payloadDepends, err := parsePayloadDepends(c)
	if err != nil {
		return err
	}

	artifactVersion, err := getImageVersion(inputZephyrImage)
	if err != nil {
		return err
	}

	payloadClearsProvides := parsePayloadClearsProvides(c)
	artifactGroup := parseArtifactGroup(c)
	compatArtifacts, compatDevices, compatGroups := parseArtifactCompatibleArtifacts(c), parseArtifactCompatibleDevices(c), parseArtifactCompatibleGroups(c)

	writer := writers.NewZephyrArtifactWriter(outputPath)
	writer.WithArtifactProvides(artifactVersion, artifactGroup)
	writer.WithArtifactDepends(compatArtifacts, compatDevices, compatGroups)
	writer.WithPayloadProvides(payloadProvides)
	writer.WithPayloadDepends(payloadDepends)
	writer.WithPayloadClearsProvides(payloadClearsProvides)
	if err := writer.WithFullZephyrPayload(inputZephyrImage, artifactVersion); err != nil {
		return err
	}

	log.Println("Writing full Zephyr artifact...")
	return writer.Write()
}

func getImageVersion(pathToImage string) (string, error) {
	file, err := os.Open(pathToImage)
	if err != nil {
		return "", nil
	}
	defer file.Close()

	// https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/mcuboot/design.html#image-format
	// Image version is embedded in image header at offset of 20 bytes
	if _, err := file.Seek(20, 0); err != nil {
		return "", err
	}

	var major, minor uint8
	var revision uint16
	var buildNum uint32

	if err := binary.Read(file, binary.LittleEndian, &major); err != nil {
		return "", err
	}
	if err := binary.Read(file, binary.LittleEndian, &minor); err != nil {
		return "", err
	}
	if err := binary.Read(file, binary.LittleEndian, &revision); err != nil {
		return "", err
	}
	if err := binary.Read(file, binary.LittleEndian, &buildNum); err != nil {
		return "", err
	}

	if buildNum == 0 {
		return fmt.Sprintf("%d.%d.%d", major, minor, revision), nil
	}

	return fmt.Sprintf("%d.%d.%d+%d", major, minor, revision, buildNum), nil
}
