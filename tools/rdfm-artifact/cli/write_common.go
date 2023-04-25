package cli

import (
	"fmt"
	"strings"

	"github.com/urfave/cli"
)

const (
	defaultFullArtifactPath = "artifact.rdfm"

	// Flag names
	flagOutputPathName   = "output-path"
	flagArtifactName     = "artifact-name"
	flagDeviceType       = "device-type"
	flagDependsArtifacts = "depends-artifacts"
	flagDependsGroups    = "depends-groups"
	flagProvidesGroup    = "provides-group"
	flagClearsProvides   = "clears-provides"
	flagProvides         = "provides"
	flagDepends          = "depends"
)

// Flags common across the different artifact modification subcommands
func makeCommonArtifactModificationFlags() []cli.Flag {
	return []cli.Flag{
		cli.StringFlag{
			Name:  flagOutputPathName,
			Usage: "Path to the output artifact. Defaults to " + defaultFullArtifactPath,
		},
		cli.StringSliceFlag{
			Name:  flagDependsArtifacts,
			Usage: "Artifact names this artifact depends on. Can be provided multiple times",
		},
		cli.StringSliceFlag{
			Name:  flagDependsGroups,
			Usage: "Group names this artifact depends on. Can be provided multiple times",
		},
		cli.StringFlag{
			Name:  flagProvidesGroup,
			Usage: "Group name provided by this artifact",
		},
		cli.StringSliceFlag{
			Name:  flagClearsProvides,
			Usage: "Provides cleared by this artifact. Can be provided multiple times",
		},
		cli.StringSliceFlag{
			Name:  flagProvides,
			Usage: "Provides (KEY:VALUE pairs) set by this artifact. Can be provided multiple times",
		},
		cli.StringSliceFlag{
			Name:  flagDepends,
			Usage: "Depends (KEY:VALUE pairs) required by this artifact. Can be provided multiple times",
		},
	}
}

// Simple helper to turn "KEY:VALUE"-type pairs into a dictionary
// Returns an error on failure
func parseKeyValuePairs(pairs []string) (map[string]string, error) {
	dict := map[string]string{}
	for _, pair := range pairs {
		parts := strings.Split(pair, ":")
		if len(parts) != 2 {
			return nil, fmt.Errorf("malformed key-value pair: %q", pair)
		}
		dict[parts[0]] = parts[1]
	}
	return dict, nil
}

func parseArtifactName(c *cli.Context) string {
	return c.String(flagArtifactName)
}

func parseArtifactGroup(c *cli.Context) string {
	return c.String(flagProvidesGroup)
}

func parseArtifactCompatibleArtifacts(c *cli.Context) []string {
	return c.StringSlice(flagDependsArtifacts)
}

func parseArtifactCompatibleDevices(c *cli.Context) []string {
	return c.StringSlice(flagDeviceType)
}

func parseArtifactCompatibleGroups(c *cli.Context) []string {
	return c.StringSlice(flagDependsGroups)
}

func parsePayloadProvides(c *cli.Context) (map[string]string, error) {
	v, err := parseKeyValuePairs(c.StringSlice(flagProvides))
	return v, err
}

func parsePayloadDepends(c *cli.Context) (map[string]string, error) {
	v, err := parseKeyValuePairs(c.StringSlice(flagDepends))
	return v, err
}

func parsePayloadClearsProvides(c *cli.Context) []string {
	return c.StringSlice(flagClearsProvides)
}

func parseOutputPath(c *cli.Context) string {
	v := c.String(flagOutputPathName)
	if v == "" {
		v = defaultFullArtifactPath
	}
	return v
}
