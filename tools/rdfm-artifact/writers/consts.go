package writers

const (
	rdfmArtifactVersion         = 3
	rdfmArtifactFormat          = "rdfm"
	rdfmRootfsArtifactDeltaType = "rootfs-image"

	rdfmRootfsProvidesChecksum = "rootfs-image.checksum"
	rdfmRootfsProvidesVersion  = "rootfs-image.version"

	rdfmRootfsDependsXdelta = "rdfm.software.supports_xdelta"
	rdfmRootfsDependsRsync  = "rdfm.software.supports_rsync"

	rdfmZephyrProvidesChecksum = "zephyr-image.checksum"
	rdfmZephyrProvidesVersion  = "zephyr-image.version"

	rdfmGroupProvidesTarget  = "zephyr-group-image.target"
	rdfmGroupProvidesVersion = "zephyr-group-image.version"
)
