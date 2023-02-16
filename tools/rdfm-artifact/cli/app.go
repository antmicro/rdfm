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
	return []cli.Command{}
}

func makeFlags() []cli.Flag {
	return []cli.Flag{}
}
