package cli

import (
	"fmt"

	"github.com/antmicro/rdfm/rdfm"
	log "github.com/sirupsen/logrus"

	//  Watch out for package name collisions with the library below
	libcli "github.com/urfave/cli/v2"
)

const (
	cliToolName                  = "rdfm"
	cliToolDescription           = "manage RDFM artifact deployment"
	cliToolMissingArgumentFormat = "missing argument: %s"
	cliToolLogLevelFlagName      = "log-level"
)

func NewApp() libcli.App {
	cliApp := &libcli.App{
		Before: handleAppFlags,
		Name:   cliToolName,
		Usage:  cliToolDescription,
	}

	cliApp.Commands = makeCommands()
	cliApp.Flags = makeFlags()

	return *cliApp
}

func makeCommands() []*libcli.Command {
	return []*libcli.Command{
		{
			Name:    "install",
			Aliases: []string{},
			Usage:   "install an artifact to the device",
			Action:  dispatchArtifactCommand,
		},
		{
			Name:    "commit",
			Aliases: []string{},
			Usage:   "commit an update, making it permanent",
			Action:  dispatchArtifactCommand,
		},
		{
			Name:    "rollback",
			Aliases: []string{},
			Usage:   "rollback to the previously installed artifact",
			Action:  dispatchArtifactCommand,
		},
		{
			Name:    "show-artifact",
			Aliases: []string{},
			Usage:   "show the name of the currently installed artifact",
			Action:  dispatchArtifactCommand,
		},
		{
			Name:    "show-provides",
			Aliases: []string{},
			Usage:   "show the current artifact's provides",
			Action:  dispatchArtifactCommand,
		},
	}
}

func makeFlags() []libcli.Flag {
	return []libcli.Flag{
		&libcli.StringFlag{
			Name:  cliToolLogLevelFlagName,
			Usage: "Log level to use",
			Value: "info",
		},
	}
}

func handleAppFlags(ctx *libcli.Context) error {
	// Handle log options
	level, err := log.ParseLevel(ctx.String(cliToolLogLevelFlagName))
	if err != nil {
		return err
	}
	log.SetLevel(level)
	return nil
}

func dispatchArtifactCommand(c *libcli.Context) error {
	//  When printing the artifact name and provides, set the log level to warn if
	//  not specified otherwise for cleaner output.
	if (c.Command.Name == "show-artifact" || c.Command.Name == "show-provides") && !c.IsSet(cliToolLogLevelFlagName) {
		log.SetLevel(log.WarnLevel)
	}

	ctx, err := rdfm.NewContext()
	if err != nil {
		return err
	}

	switch c.Command.Name {
	case "install":
		{
			if c.NArg() != 1 {
				return fmt.Errorf(cliToolMissingArgumentFormat, "path to artifact")
			}
			return ctx.InstallArtifact(c.Args().Get(0))
		}
	case "commit":
		{
			return ctx.CommitCurrentArtifact()
		}
	case "rollback":
		{
			return ctx.RollbackCurrentArtifact()
		}
	case "show-artifact":
		{
			name, err := ctx.GetCurrentArtifactName()
			if err != nil {
				return err
			}

			fmt.Println(name)
			return nil
		}
	case "show-provides":
		{
			provides, err := ctx.GetCurrentArtifactProvides()
			if err != nil {
				return err
			}

			for k, v := range provides {
				fmt.Printf("%s=%s\n", k, v)
			}

			return nil
		}
	}

	panic("should never be reached")
}
