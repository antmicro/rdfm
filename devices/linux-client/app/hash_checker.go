package app

import (
	"crypto/sha256"
	"hash"
	"encoding/hex"

	log "github.com/sirupsen/logrus"
)

type ArtifactHashChecker struct {
	hashWriter hash.Hash
	imageSize int64
	imageHash string
	finalHash string
	bytesWritten int64
}

func newArtifactHashChecker(imageSize int64, imageHash string) *ArtifactHashChecker {
	return &ArtifactHashChecker {
		hashWriter: sha256.New(),
		imageSize: imageSize,
		imageHash: imageHash,
		bytesWritten: 0,
	}
}

func (a *ArtifactHashChecker) Write(p []byte) (n int, err error) {
	a.hashWriter.Write(p)
	n = len(p)
	a.bytesWritten += int64(n)
	if a.bytesWritten >= a.imageSize {
		a.finalHash = hex.EncodeToString(a.hashWriter.Sum(nil))
		if a.imageHash != "" && a.imageHash != a.finalHash {
			log.Errorf("The installed artifact's hash isn't correct (expected=%s, got=%s)", a.imageHash, a.finalHash)
		}
	}
	return n, nil
}
