package app

import (
	"os"
	"path"
)

const (
	RdfmConfigDirectory      = "/etc/rdfm"
	RdfmDataDirectory        = "/var/lib/rdfm"
	RdfmConfigFilename       = "rdfm.conf"
	RdfmTokenFilename        = "token.json"
	RdfmArtifactInfoFilename = "artifact_info"
	RdfmProvidesInfoFilename = "provides_info"
)

var (
	RdfmTokenDirectory    = os.Getenv("HOME")
	RdfmDefaultConfigPath = path.Join(RdfmConfigDirectory, RdfmConfigFilename)
	RdfmOverlayConfigPath = path.Join(RdfmDataDirectory, RdfmConfigFilename)
	RdfmArtifactInfoPath  = path.Join(RdfmConfigDirectory, RdfmArtifactInfoFilename)
	RdfmProvidesInfoPath  = path.Join(RdfmConfigDirectory, RdfmProvidesInfoFilename)
	RdfmTokenPath         = path.Join(RdfmTokenDirectory, RdfmTokenFilename)
)
