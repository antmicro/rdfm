package cli

import "github.com/urfave/cli"

const (
	cliToolName        = "rdfm-artifact"
	cliToolDescription = "manage creation of RDFM artifacts"
	cliToolVersion     = "0.1.0"
)

func NewApp() *cli.App {
	app := &cli.App{
		Name:    cliToolName,
		Usage:   cliToolDescription,
		Version: cliToolVersion,
	}
	app.Commands = makeCommands()
	app.Flags = makeFlags()

	return app
}

func makeCommands() []cli.Command {
	return []cli.Command{
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
					Flags:  makeDeltaRootfsFlags(),
					Action: writeDeltaRootfs,
				},
			},
		},
	}
}

func makeFlags() []cli.Flag {
	return []cli.Flag{}
}
