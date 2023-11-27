package app

import (
	"path"
)

const (
	RdfmConfigDirectory      = "/etc/rdfm"
	RdfmDataDirectory        = "/var/lib/rdfm"
	RdfmConfigFilename       = "rdfm.conf"
	RdfmArtifactInfoFilename = "artifact_info"
	RdfmProvidesInfoFilename = "provides_info"
	RdfmRSAKeysFilename      = "rsa.pem"
)

var (
	RdfmDefaultConfigPath = path.Join(RdfmConfigDirectory, RdfmConfigFilename)
	RdfmOverlayConfigPath = path.Join(RdfmDataDirectory, RdfmConfigFilename)
	RdfmArtifactInfoPath  = path.Join(RdfmConfigDirectory, RdfmArtifactInfoFilename)
	RdfmProvidesInfoPath  = path.Join(RdfmConfigDirectory, RdfmProvidesInfoFilename)
	RdfmRSAKeysPath       = path.Join(RdfmDataDirectory, RdfmRSAKeysFilename)
)
