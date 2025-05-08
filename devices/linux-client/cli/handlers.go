package cli

import (
	"fmt"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/daemon"
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
			Name:    "show-device",
			Aliases: []string{},
			Usage:   "show the current device type",
			Action:  dispatchArtifactCommand,
		},
		{
			Name:    "show-provides",
			Aliases: []string{},
			Usage:   "show the current artifact's provides",
			Action:  dispatchArtifactCommand,
		},
		{
			Name:    "daemonize",
			Aliases: []string{},
			Usage:   "start in daemon mode",
			Description: `Mode maintaining connection to the server,
						  providing management functionalities,
						  like proxy connection, file transfer,
						  metadata collection, and automatic
						  updates installation`,
			Action: daemon.Daemonize,
			Flags: []libcli.Flag{
				&libcli.StringFlag{
					Name:    "name",
					Aliases: []string{"n"},
					Usage:   "Name for identification",
					Value:   "dummy_device",
				},
				&libcli.StringFlag{
					Name:  "file-metadata",
					Usage: "File containing device metadata",
					Value: "tests/testdata.json",
				},
			},
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
	//  When printing the artifact name, device type and provides, set the log level
	//  to warn if not specified otherwise for cleaner output.
	if (c.Command.Name == "show-artifact" || c.Command.Name == "show-provides" ||
		c.Command.Name == "show-device") && !c.IsSet(cliToolLogLevelFlagName) {
		log.SetLevel(log.WarnLevel)
	}

	ctx, err := app.NewRdfmContext()
	if err != nil {
		return err
	}

	switch c.Command.Name {
	case "install":
		if c.NArg() != 1 {
			return fmt.Errorf(cliToolMissingArgumentFormat, "path to artifact")
		}
		return ctx.InstallArtifact(c.Args().Get(0))

	case "commit":
		return ctx.CommitCurrentArtifact()

	case "rollback":
		return ctx.RollbackCurrentArtifact()

	case "show-artifact":
		name, err := ctx.GetCurrentArtifactName()
		if err != nil {
			return err
		}
		fmt.Println(name)
		return nil

	case "show-device":
		device, err := ctx.GetCurrentDeviceType()
		if err != nil {
			return err
		}
		fmt.Println(device)
		return nil

	case "show-provides":
		provides, err := ctx.GetCurrentArtifactProvides()
		if err != nil {
			return err
		}
		for k, v := range provides {
			fmt.Printf("%s=%s\n", k, v)
		}
		return nil

	default:
		panic("should never be reached")
	}
}
