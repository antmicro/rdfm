package cli

import (
	"log"

	"github.com/antmicro/rdfm-artifact/writers"
	"github.com/urfave/cli"
)

const (
	flagBaseArtifactPath   = "base-artifact"
	flagTargetArtifactPath = "target-artifact"
)

func makeDeltaRootfsFlags() []cli.Flag {
	return append(makeCommonArtifactModificationFlags(),
		cli.StringFlag{
			Name:  flagArtifactName,
			Usage: "Name of the artifact",
		},
		cli.StringSliceFlag{
			Name:  flagDeviceType,
			Usage: "Device type this artifact is compatible with. Can be provided multiple times",
		},
		cli.StringFlag{
			Name:     flagBaseArtifactPath,
			Usage:    "Path to the base artifact",
			Required: true,
		},
		cli.StringFlag{
			Name:     flagTargetArtifactPath,
			Usage:    "Path to the target artifact",
			Required: true,
		},
	)
}

func writeDeltaRootfs(c *cli.Context) error {
	baseArtifact := c.String(flagBaseArtifactPath)
	targetArtifact := c.String(flagTargetArtifactPath)
	outputPath := parseOutputPath(c)

	log.Println("Base artifact:", baseArtifact)
	log.Println("Target artifact:", targetArtifact)

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
	writer.WithDeltaRootfsPayload(baseArtifact, targetArtifact)

	log.Println("Writing delta artifact...")
	return writer.Write()
}
