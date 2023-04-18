package deltas

import (
	"errors"
	"io"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"golang.org/x/sync/errgroup"
)

func TestDeltaPatcher(t *testing.T) {
	patcher := NewArtifactDelta("../tests/data/delta-base.rdfm", "../tests/data/delta-target.rdfm")

	var wg errgroup.Group

	wg.Go(func() error {
		// TODO: add a check for whether the deltas are correct
		out, err := os.OpenFile("../tests/data/delta-output-test.bin", os.O_CREATE|os.O_RDWR, 0660)
		if err != nil {
			return err
		}

		// We just copy the file contents to a temp file here
		written, err := io.Copy(out, patcher.Reader())
		if err != nil {
			return err
		}

		if written <= 0 {
			return errors.New("did not write any bytes!")
		}
		return nil
	})

	err := patcher.Delta()
	assert.Nil(t, err)
	err = wg.Wait()
	assert.Nil(t, err)
}
