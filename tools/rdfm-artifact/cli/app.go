package cli

import (
	"fmt"

	"github.com/urfave/cli"
)

const (
	cliToolName        = "rdfm-artifact"
	cliToolDescription = "manage creation of RDFM artifacts"
	noPositional       = " " // needs to be truthy so the default [arguments...] is not displayed
)

// Version of the rdfm-artifact CLI tool
var Version = "unknown"

func NewApp() *cli.App {
	app := &cli.App{
		Name:    cliToolName,
		Usage:   cliToolDescription,
		Version: Version,
	}
	app.Commands = makeCommands()
	app.Flags = makeFlags()

	return app
}

func walkCommands(cmds cli.Commands, fn func(*cli.Command)) {
	for i := range cmds {
		c := &cmds[i]
		fn(c)
		if len(c.Subcommands) > 0 {
			walkCommands(c.Subcommands, fn)
		}
	}
}

func makeCommands() []cli.Command {
	cmds := []cli.Command{
		{
			Name:        "read",
			Aliases:     []string{"r"},
			Usage:       "Read artifact contents",
			ArgsUsage:   "<path to artifact>",
			HelpName:    "rdfm-artifact read",
			Description: "Allows reading the contents of an artifact. Displays the artifact metadata and contained payloads.",
			Action:      readArtifact,
		},
		{
			Name:        "write",
			Aliases:     []string{"w"},
			Usage:       "Create an artifact",
			Description: "Allows creation of RDFM-compatible artifacts",
			Subcommands: []cli.Command{
				{
					Name:        "rootfs-image",
					Usage:       "Create a full rootfs image artifact",
					Description: "Creates a non-delta artifact containing the complete rootfs partition image to be installed on a target device",
					Flags:       makeFullRootfsFlags(),
					ArgsUsage:   "<path to rootfs image>",
					Action:      writeFullRootfs,
				},
				{
					Name:  "delta-rootfs-image",
					Usage: "Create a delta rootfs artifact",
					Description: `Creates a delta rootfs artifact, which uses binary deltas to reduce the size of an update. This requires two full rootfs image artifacts to be passed:
		- "source" artifact - base artifact the delta will be applied on top of, i.e the currently running software
		- "destination" artifact - target artifact, i.e the updated version of the running software
					`,
					Flags:     makeDeltaRootfsFlags(),
					ArgsUsage: noPositional,
					Action:    writeDeltaRootfs,
				},
				{
					Name:        "zephyr-image",
					Usage:       "Create a full Zephyr MCUboot image artifact",
					Description: "Creates a non-delta artifact containing the complete Zephyr MCUboot image to be installed on a target device",
					Flags:       makeFullZephyrFlags(),
					ArgsUsage:   noPositional,
					Action:      writeFullZephyr,
				},
				{
					Name:        "zephyr-group-image",
					Usage:       "Create a Zephyr MCUboot group image artifact",
					Description: "Creates an artifact containing update images for Zephyr group devices",
					Flags:       makeGroupFlags(),
					ArgsUsage:   noPositional,
					Action:      writeGroupZephyr,
				},
				{
					Name:        "single-file",
					Usage:       "Create a single file artifact",
					Description: "Creates an artifact containing a single file that can be installed on a target device",
					Flags:       makeSingleFileFlags(),
					ArgsUsage:   noPositional,
					Action:      writeSingleFile,
				},
			},
		},
	}

	walkCommands(cmds, func(cmd *cli.Command) {
		if cmd.ArgsUsage != noPositional {
			return
		}
		cmd.Before = func(c *cli.Context) error {
			if c.Args().Present() {
				return fmt.Errorf("%v: unexpected positional arguments: %v", cmd.Name, c.Args())
			}
			return nil
		}
	})

	return cmds
}

func makeFlags() []cli.Flag {
	return []cli.Flag{}
}
