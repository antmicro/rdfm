package conf

import (
	"path"
)

const (
	RdfmConfigDirectory      = "/etc/rdfm"
	RdfmDataDirectory        = "/var/lib/rdfm"
	RdfmConfigFilename       = "rdfm.conf"
	RdfmLoggersFilename      = "loggers.conf"
	RdfmArtifactInfoFilename = "artifact_info"
	RdfmProvidesInfoFilename = "provides_info"
	RdfmDeviceIdFilename     = "device_id"
	RdfmRSAKeysFilename      = "rsa.pem"
	RdfmCacheDirectory       = "cache"
	RdfmActionsFilename      = "actions.conf"
	RdfmActionDataDirectory  = "action_persist"
	RdfmTagsFilename         = "tags.conf"
	// This pattern can only contain one '*', because of the Sprintf use in cached_fetcher
	RdfmCacheFilePattern = "update-*.cache"
)

var (
	RdfmDefaultConfigPath  = path.Join(RdfmConfigDirectory, RdfmConfigFilename)
	RdfmOverlayConfigPath  = path.Join(RdfmDataDirectory, RdfmConfigFilename)
	RdfmDefaultLoggersPath = path.Join(RdfmConfigDirectory, RdfmLoggersFilename)
	RdfmArtifactInfoPath   = path.Join(RdfmConfigDirectory, RdfmArtifactInfoFilename)
	RdfmProvidesInfoPath   = path.Join(RdfmConfigDirectory, RdfmProvidesInfoFilename)
	RdfmDeviceIdPath       = path.Join(RdfmDataDirectory, RdfmDeviceIdFilename)
	RdfmRSAKeysPath        = path.Join(RdfmDataDirectory, RdfmRSAKeysFilename)
	RdfmCachePath          = path.Join(RdfmDataDirectory, RdfmCacheDirectory)
	RdfmDefaultActionsPath = path.Join(RdfmDataDirectory, RdfmActionsFilename)
	RdfmActionDataPath     = path.Join(RdfmDataDirectory, RdfmActionDataDirectory)
	RdfmDefaultTagsPath    = path.Join(RdfmDataDirectory, RdfmTagsFilename)
)
