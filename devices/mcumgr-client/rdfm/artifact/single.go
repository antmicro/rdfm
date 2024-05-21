package artifact

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"

	"github.com/mendersoftware/mender-artifact/areader"
)

const ZephyrArtifactPrefix = "zephyr-image"

// Artifact holding a single update image for
// cmopatible devices
type ZephyrArtifact struct {
	Image      []byte
	Version    string
	Compatible []string
}

func ExtractZephyrArtifact(reader *areader.Reader) (*ZephyrArtifact, error) {
	store, err := ReadArtifactToMem(reader)
	if err != nil {
		return nil, err
	}

	// Image extraction
	if fileCnt := len(store.ExtractedFiles); fileCnt != 1 {
		return nil, errors.New(fmt.Sprintf("Unexpected file count in artifact (expected 1, got %d)", fileCnt))
	}

	var image []byte
	for _, v := range store.ExtractedFiles {
		image = v
	}

	compatible, provides, err := ExtractArtifactCommon(reader)
	if err != nil {
		return nil, err
	}

	expectedHash, ok := provides[fmt.Sprintf("%s.checksum", ZephyrArtifactPrefix)]
	if !ok {
		return nil, errors.New("Artifact should contain image checksum")
	}

	imageHash := sha256.Sum256(image)
	if hex.EncodeToString(imageHash[:]) != strings.ToLower(expectedHash) {
		return nil, errors.New(fmt.Sprintf("Artifact contents malformed"))
	}

	imageVersion, ok := provides[fmt.Sprintf("%s.version", ZephyrArtifactPrefix)]
	if !ok {
		return nil, errors.New("Artifact should contain image version")
	}

	return &ZephyrArtifact{
		Image:      image,
		Version:    imageVersion,
		Compatible: compatible,
	}, nil
}

func (za *ZephyrArtifact) String() string {
	return fmt.Sprintf("Zephyr artifact: version %s, size %d bytes", za.Version, len(za.Image))
}
