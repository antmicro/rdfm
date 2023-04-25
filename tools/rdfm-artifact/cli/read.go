package cli

import (
	artifactcli "github.com/mendersoftware/mender-artifact/cli"
	"github.com/pkg/errors"
	"github.com/urfave/cli"
)

func readArtifact(c *cli.Context) error {
	if len(c.Args()) != 1 {
		return errors.Errorf("expected 1 argument (path to artifact), got %v instead", len(c.Args()))
	}
	artifact := c.Args()[0]

	return artifactcli.Run(
		[]string{
			"rdfm-artifact",
			"read",
			artifact,
		})
}
