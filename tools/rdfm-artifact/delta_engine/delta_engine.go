package delta_engine

import (
	"fmt"
	"io"

	"github.com/antmicro/go-xdelta/xdelta3/go_api"
	"github.com/balena-os/librsync-go"
)

type DeltaAlgorithmEngine interface {
	// Name returns the canonical algorithm name ("rsync" or "xdelta")
	Name() string
	// Delta reads base and target and writes a delta file to output
	Delta(base io.Reader, target io.Reader, out io.Writer) error
	// Patch applies a patch onto base, writing the result into output
	Patch(base io.ReadSeeker, delta io.Reader, out io.Writer) error
	// Metadata returns RDFM‑style metadata entries for delta algorithm.
	// Prefix the keys with:
	//   - "requires:" to indicate they belong in ArtifactDepends
	//   - "provides:" to indicate they belong in ArtifactProvides
	//
	// e.g. {"requires:rdfm.software.supports_xdelta":"true"}
	Metadata() map[string]string
}

func ParseDeltaEngine(algo string) (DeltaAlgorithmEngine, error) {
	switch algo {
	case "rsync":
		return &rsyncEngine{}, nil
	case "xdelta":
		return &xdeltaEngine{}, nil
	default:
		return nil, fmt.Errorf("invalid delta algorithm %q; want \"rsync\" or \"xdelta\"", algo)
	}
}

type rsyncEngine struct{}

func (*rsyncEngine) Name() string { return "rsync" }
func (*rsyncEngine) Delta(base io.Reader, target io.Reader, out io.Writer) error {
	sig, err := librsync.Signature(base, io.Discard, DeltaBlockLength, DeltaStrongLength, DeltaSignatureType)
	if err != nil {
		return err
	}
	return librsync.Delta(sig, target, out)
}
func (*rsyncEngine) Patch(base io.ReadSeeker, delta io.Reader, out io.Writer) error {
	return librsync.Patch(base, delta, out)
}
func (e *rsyncEngine) Metadata() map[string]string {
	return map[string]string{
		fmt.Sprintf("requires:rdfm.software.supports_%s", e.Name()): "true",
	}
}

type xdeltaEngine struct{}

func (*xdeltaEngine) Name() string { return "xdelta" }
func (*xdeltaEngine) Delta(base io.Reader, target io.Reader, out io.Writer) error {
	return xdelta.Xd3Encode(base, target, out)
}
func (*xdeltaEngine) Patch(base io.ReadSeeker, delta io.Reader, out io.Writer) error {
	return xdelta.Xd3Decode(base, delta, out)
}
func (e *xdeltaEngine) Metadata() map[string]string {
	return map[string]string{
		fmt.Sprintf("requires:rdfm.software.supports_%s", e.Name()): "true",
	}
}
