package deltas

import "github.com/balena-os/librsync-go"

const (
	DeltaBlockLength   = uint32(4096)
	DeltaStrongLength  = uint32(32)
	DeltaSignatureType = librsync.BLAKE2_SIG_MAGIC
)
