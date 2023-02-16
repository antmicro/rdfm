package cli

import (
	"fmt"
	"os"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"
	"github.com/urfave/cli"
)

func makeFullRootfsFlags() []cli.Flag {
	return append(makeCommonArtifactModificationFlags(),
		cli.StringFlag{
			Name:  flagOutputPathName,
			Usage: "path to the output artifact",
			Value: defaultFullArtifactPath,
		})
}

func writeFullRootfs(c *cli.Context) error {
	if c.NArg() != 1 {
		return fmt.Errorf("expected 1 argument (rootfs image), got %d instead", c.NArg())
	}
	inputRootfsImage := c.Args().Get(0)

	args, err := makeCommonArtifactWriterArgs(c)
	if err != nil {
		return err
	}
	args.Updates = &awriter.Updates{
		Updates: []handlers.Composer{handlers.NewRootfsV3(inputRootfsImage)},
	}

	f, err := os.OpenFile(c.String(flagOutputPathName), os.O_CREATE|os.O_WRONLY, 0660)
	if err != nil {
		return err
	}
	defer f.Close()

	writer := awriter.NewWriter(f, artifact.NewCompressorNone())
	err = writer.WriteArtifact(args)
	if err != nil {
		return err
	}

	return nil
}
