package main

import (
	"fmt"
	"os"

	"github.com/antmicro/rdfm/devices/linux-client/cli"
)

func main() {
	app := cli.NewApp()
	err := app.Run(os.Args)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
