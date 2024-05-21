package artifact

import (
	"crypto/sha256"
	"errors"
	"fmt"

	"github.com/mendersoftware/mender-artifact/areader"
)

const (
	GroupArtifactPrefix  = "zephyr-group-image"
	GroupArtifactVersion = GroupArtifactPrefix + ".version"

	GroupArtifactTarget = GroupArtifactPrefix + ".target"
)

// Artifact holding group of update images for
// for specific device group
type GroupArtifact struct {
	Images     map[string]AFile
	Version    string
	Compatible []string
}

func ExtractGroupArtifact(reader *areader.Reader) (*GroupArtifact, error) {
	store, err := ReadArtifactToMem(reader)
	if err != nil {
		return nil, err
	}

	compatible, provides, err := ExtractArtifactCommon(reader)
	if err != nil {
		return nil, err
	}

	devImgMap := make(map[string]AFile, len(store.ExtractedFiles))
	for name, image := range store.ExtractedFiles {
		hash := sha256.Sum256(image)

		expectedHash, ok := provides[fmt.Sprintf("%s.%s", GroupArtifactTarget, name)]
		if !ok {
			return nil, errors.New(fmt.Sprintf("Unknown image '%s' in artifact", name))
		}
		if expectedHash != fmt.Sprintf("%x", hash) {
			return nil, errors.New(fmt.Sprintf("Checksum mismatch for '%s' image", name))
		}

		devImgMap[name] = AFile{
			Data: image,
			Hash: hash[:],
		}
	}

	version, ok := provides[GroupArtifactVersion]
	if !ok {
		return nil, errors.New("Artifact should contain image version")
	}

	return &GroupArtifact{
		Images:     devImgMap,
		Version:    version,
		Compatible: compatible,
	}, nil
}

func (ga *GroupArtifact) String() string {
	var targets string
	for k := range ga.Images {
		targets += k + ", "
	}
	return fmt.Sprintf("Group artifact: version %s, %d images, targets [%s]", ga.Version, len(ga.Images), targets[:len(targets)-2])
}
