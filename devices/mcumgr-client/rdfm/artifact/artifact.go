package artifact

import (
	"errors"
	"fmt"
	"io"

	"github.com/mendersoftware/mender-artifact/areader"
)

type Artifact interface {
	fmt.Stringer
}

func ExtractArtifact(r io.Reader) (Artifact, error) {
	reader := areader.NewReader(r)

	err := reader.ReadArtifactHeaders()
	if err != nil {
		return nil, err
	}

	updates := reader.GetUpdates()
	if len(updates) == 0 {
		return nil, errors.New("Artifact provides no updates")
	}

	// Extract different artifact based on the type
	switch *updates[0].Type {
	case ZephyrArtifactPrefix:
		return ExtractZephyrArtifact(reader)
	default:
		return nil, errors.New(fmt.Sprintf("Unknown artifact type '%s'", *updates[0].Type))
	}
}
