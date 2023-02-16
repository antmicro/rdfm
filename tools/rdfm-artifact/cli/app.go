package cli

import "github.com/urfave/cli"

func NewApp() *cli.App {
	app := cli.NewApp()

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
