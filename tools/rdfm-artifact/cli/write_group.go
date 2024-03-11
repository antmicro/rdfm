package cli

import (
	"fmt"
	"log"
	"strings"

	"github.com/antmicro/rdfm-artifact/writers"
	"github.com/urfave/cli"
)

func makeGroupFlags() []cli.Flag {
	return append(makeCommonArtifactModificationFlags(),
		cli.StringSliceFlag{
			Name:     "group-type",
			Usage:    "Group type this artifact is compatible with. Can be provided multiple times",
			Required: true,
		},
		cli.StringSliceFlag{
			Name:     "target",
			Usage:    "Update target in the form of 'device:image_path'. Can be provided multiple times",
			Required: true,
		},
	)
}

func writeGroupZephyr(c *cli.Context) error {
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
	artifactGroup := parseArtifactGroup(c)
	compatArtifacts, compatGroups := parseArtifactCompatibleArtifacts(c), parseArtifactCompatibleGroups(c)

	compatDevices := c.StringSlice("group-type")

	inputTargets := c.StringSlice("target")
	devFileMap := make(map[string]string, len(inputTargets))
	for _, it := range inputTargets {
		split := strings.Split(it, ":")
		if len(split) != 2 {
			return fmt.Errorf("Invalid target format (expected 'device:path', got '%s')", it)
		}

		devFileMap[split[0]] = split[1]
	}

	var artifactVersion string
	for _, val := range devFileMap {
		artifactVersion, err = getImageVersion(val)
		if err != nil {
			return err
		}
		break
	}

	writer := writers.NewGroupArtifactWriter(outputPath)
	writer.WithArtifactProvides(artifactVersion, artifactGroup)
	writer.WithArtifactDepends(compatArtifacts, compatDevices, compatGroups)
	writer.WithPayloadProvides(payloadProvides)
	writer.WithPayloadDepends(payloadDepends)
	writer.WithPayloadClearsProvides(payloadClearsProvides)
	if err := writer.WithGroupPayload(devFileMap, artifactVersion); err != nil {
		return err
	}

	log.Println("Writing group Zephyr artifact...")
	return writer.Write()
}
