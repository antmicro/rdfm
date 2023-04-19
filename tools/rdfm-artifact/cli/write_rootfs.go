package cli

import (
	"fmt"
	"log"

	"github.com/antmicro/rdfm-artifact/writers"
	"github.com/urfave/cli"
)

func makeFullRootfsFlags() []cli.Flag {
	return makeCommonArtifactModificationFlags()
}

func writeFullRootfs(c *cli.Context) error {
	if c.NArg() != 1 {
		return fmt.Errorf("expected 1 argument (rootfs image), got %d instead", c.NArg())
	}
	inputRootfsImage := c.Args().Get(0)

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
