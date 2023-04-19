package cli

import (
	"fmt"
	"strings"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/urfave/cli"
)

const (
	defaultFullArtifactPath = "artifact.rdfm"

	// Data reported in the artifact
	writerArtifactFormat         = "mender"
	writerArtifactVersion        = 3
	writerArtifactFullRootfsType = "rootfs-image"

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

	// Keys for specific values in the provides dictionary
	providesArtifactNameKey = "artifact_name"
	providesDeviceTypeKey   = "device_type"
)

// Flags common across the different artifact modification subcommands
func makeCommonArtifactModificationFlags() []cli.Flag {
	return []cli.Flag{
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

func parseDependsValues(args []string) (artifact.TypeInfoDepends, error) {
	typeInfoArtifactDepends, err := parseKeyValuePairs(args)
	if err != nil {
		return nil, err
	}
	return artifact.NewTypeInfoDepends(typeInfoArtifactDepends)
}

func parseProvidesValues(args []string) (artifact.TypeInfoProvides, error) {
	typeInfoArtifactProvides, err := parseKeyValuePairs(args)
	if err != nil {
		return nil, err
	}
	return artifact.NewTypeInfoProvides(typeInfoArtifactProvides)
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

// This is a helper for extracting common CLI flags across the write subcommands (write rootfs, write delta)
// A `WriteArtifactArgs` struct is returned, with the values set from the passed in flags.
func makeCommonArtifactWriterArgs(c *cli.Context) (*awriter.WriteArtifactArgs, error) {
	dependsCompatibleDevices := c.StringSlice(flagDeviceType)
	dependsArtifactName := c.StringSlice(flagDependsArtifacts)
	dependsArtifactGroup := c.StringSlice(flagDependsGroups)

	providesArtifactName := c.String(flagArtifactName)
	providesArtifactGroup := c.String(flagProvidesGroup)

	typeInfoType := writerArtifactFullRootfsType
	typeInfoArtifactDepends, err := parseDependsValues(c.StringSlice(flagDepends))
	if err != nil {
		return nil, err
	}
	typeInfoArtifactProvides, err := parseProvidesValues(c.StringSlice(flagProvides))
	if err != nil {
		return nil, err
	}
	typeInfoClearsArtifactProvides := c.StringSlice(flagClearsProvides)

	args := awriter.WriteArtifactArgs{
		Name:    flagOutputPathName,
		Format:  writerArtifactFormat,
		Version: 3,
		// Artifact depends on one of the following
		Depends: &artifact.ArtifactDepends{
			ArtifactName:      dependsArtifactName,
			CompatibleDevices: dependsCompatibleDevices,
			ArtifactGroup:     dependsArtifactGroup,
		},
		// Artifact provides this name and group
		Provides: &artifact.ArtifactProvides{
			ArtifactName:  providesArtifactName,
			ArtifactGroup: providesArtifactGroup,
		},
		// Additional provides
		// This is for example the rootfs-image.checksum value
		TypeInfoV3: &artifact.TypeInfoV3{
			Type:                   &typeInfoType,
			ArtifactDepends:        typeInfoArtifactDepends,
			ArtifactProvides:       typeInfoArtifactProvides,
			ClearsArtifactProvides: typeInfoClearsArtifactProvides,
		},
		// What updates are contained within this artifact?
		// In general, rootfs contain only a single file (the updated rootfs image)
		// Leaving this empty to be filled by the rootfs/delta writer handlers
		Updates: &awriter.Updates{},
		// These are only relevant for version 2 artifacts
		// We only create version 3 artifacts
		Devices: []string{},
		Scripts: &artifact.Scripts{},
		// Below are unused by rdfm, but they still exist
		MetaData:          map[string]interface{}{},
		AugmentTypeInfoV3: &artifact.TypeInfoV3{},
		AugmentMetaData:   map[string]interface{}{},
		Bootstrap:         false,
	}

	return &args, nil
}
