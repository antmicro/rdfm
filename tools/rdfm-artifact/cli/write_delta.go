package cli

import (
	"log"

	"github.com/antmicro/rdfm/tools/rdfm-artifact/delta_engine"
	"github.com/antmicro/rdfm/tools/rdfm-artifact/writers"
	"github.com/urfave/cli"
)

const (
	flagBaseArtifactPath   = "base-artifact"
	flagTargetArtifactPath = "target-artifact"
	flagDeltaAlgorithm     = "delta-algorithm"
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
		cli.StringFlag{
			Name: flagDeltaAlgorithm,
			Value: "rsync", // default
			// Skipping Value field to avoid implicitly appending "(default: rsync)"
			// in help output. Default value is handled in parseDeltaAlgorithm function
			Usage: "Algorithm for delta encoding (default: rsync).\n" +
				"      Available options:\n" +
				"        - rsync  : larger delta sizes and slower encoding, faster decoding (default)\n" +
				"        - xdelta : smaller delta sizes and faster encoding, slower decoding\n" +
				"      Use 'rsync' to minimize computational load during update application on the target device, or 'xdelta' to prioritize a smaller update package size.",
		},
	)
}

func writeDeltaRootfs(c *cli.Context) error {
	baseArtifact := c.String(flagBaseArtifactPath)
	targetArtifact := c.String(flagTargetArtifactPath)
	outputPath := parseOutputPath(c)

	deltaEngine, err := delta_engine.ParseDeltaEngine(c.String(flagDeltaAlgorithm))
	if err != nil {
		return err
	}

	log.Println("Base artifact:", baseArtifact)
	log.Println("Target artifact:", targetArtifact)
	log.Println("Delta algorithm:", deltaEngine.Name())

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

	writer := writers.NewRootfsArtifactWriter(outputPath)
	writer.WithArtifactProvides(artifactName, artifactGroup)
	writer.WithArtifactDepends(compatArtifacts, compatDevices, compatGroups)
	writer.WithPayloadProvides(payloadProvides)
	writer.WithPayloadDepends(payloadDepends)
	writer.WithPayloadClearsProvides(payloadClearsProvides)
	err = writer.WithDeltaRootfsPayload(baseArtifact, targetArtifact, deltaEngine)
	if err != nil {
		return err
	}

	log.Println("Writing delta artifact...")
	return writer.Write()
}
