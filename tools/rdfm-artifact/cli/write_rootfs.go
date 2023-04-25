package cli

import (
	"log"

	"github.com/antmicro/rdfm-artifact/writers"
	"github.com/urfave/cli"
)

const (
	flagInputFilePath = "file"
)

func makeFullRootfsFlags() []cli.Flag {
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
			Usage:    "Path to the rootfs image.",
			Required: true,
		})
}

func parseInputFile(c *cli.Context) string {
	return c.String(flagInputFilePath)
}

func writeFullRootfs(c *cli.Context) error {
	inputRootfsImage := parseInputFile(c)
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

	writer := writers.NewArtifactWriter(outputPath)
	writer.WithArtifactProvides(artifactName, artifactGroup)
	writer.WithArtifactDepends(compatArtifacts, compatDevices, compatGroups)
	writer.WithPayloadProvides(payloadProvides)
	writer.WithPayloadDepends(payloadDepends)
	writer.WithPayloadClearsProvides(payloadClearsProvides)
	writer.WithFullRootfsPayload(inputRootfsImage)

	log.Println("Writing full rootfs artifact...")
	return writer.Write()
}
