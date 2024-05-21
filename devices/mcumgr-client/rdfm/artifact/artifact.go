package artifact

import (
	"errors"
	"fmt"
	"io"

	"github.com/mendersoftware/mender-artifact/areader"
)

type (
	Artifact interface {
		fmt.Stringer
	}

	AFile struct {
		Data []byte
		Hash []byte
	}
)

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
	case GroupArtifactPrefix:
		return ExtractGroupArtifact(reader)
	default:
		return nil, errors.New(fmt.Sprintf("Unknown artifact type '%s'", *updates[0].Type))
	}
}

func ExtractArtifactCommon(reader *areader.Reader) (compatible []string, provides map[string]string, err error) {
	depErr := errors.New("Artifact should contain list of compatible devices")

	// Depends extraction
	depends, err := reader.MergeArtifactDepends()
	if err != nil {
		return
	}

	comp, ok := depends["device_type"]
	if !ok {
		err = depErr
		return
	}
	compArr, ok := comp.([]interface{})
	if !ok {
		err = depErr
		return
	}

	compatible = make([]string, 0, len(compArr))
	for _, v := range compArr {
		vStr, ok := v.(string)
		if !ok {
			err = depErr
			return
		}
		compatible = append(compatible, vStr)
	}

	// Provides extraction
	provides, err = reader.MergeArtifactProvides()

	return
}
