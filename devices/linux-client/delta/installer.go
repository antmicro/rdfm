package delta

import (
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/antmicro/rdfm/third_party/block_device"
	"github.com/balena-os/librsync-go"
	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/handlers"
	"github.com/mendersoftware/mender/installer"
	"github.com/pkg/errors"
)

// This is a simple wrapper class for the original DualRootfsDevice installer.
// It requires the original DualRootfsDevice created for the current device configuration,
// to which all regular artifact installation handling is passed.
// When a delta artifact is being installed, the patch is applied onto a proper base image
// and installed to the block device.
type DeltaRootfsInstaller struct {
	installer.DualRootfsDevice

	realDev installer.DualRootfsDevice
}

func NewDeltaInstaller(realDev installer.DualRootfsDevice) DeltaRootfsInstaller {
	return DeltaRootfsInstaller{
		realDev: realDev,
	}
}

func (d DeltaRootfsInstaller) Reboot() error {
	return d.realDev.Reboot()
}

func (d DeltaRootfsInstaller) Initialize(artifactHeaders artifact.HeaderInfoer, artifactAugmentedHeaders artifact.HeaderInfoer, payloadHeaders handlers.ArtifactUpdateHeaders) error {
	return d.realDev.Initialize(artifactHeaders, artifactAugmentedHeaders, payloadHeaders)
}

func (d DeltaRootfsInstaller) PrepareStoreUpdate() error {
	return d.realDev.PrepareStoreUpdate()
}

func (d DeltaRootfsInstaller) StoreUpdate(r io.Reader, info os.FileInfo) error {
	return d.realDev.StoreUpdate(r, info)
}

func (d DeltaRootfsInstaller) FinishStoreUpdate() error {
	return d.realDev.FinishStoreUpdate()
}

func (d DeltaRootfsInstaller) InstallUpdate() error {
	return d.realDev.InstallUpdate()
}

func (d DeltaRootfsInstaller) NeedsReboot() (installer.RebootAction, error) {
	return d.realDev.NeedsReboot()
}

func (d DeltaRootfsInstaller) CommitUpdate() error {
	return d.realDev.CommitUpdate()
}

func (d DeltaRootfsInstaller) SupportsRollback() (bool, error) {
	return d.realDev.SupportsRollback()
}

func (d DeltaRootfsInstaller) Rollback() error {
	return d.realDev.Rollback()
}

func (d DeltaRootfsInstaller) VerifyReboot() error {
	return d.realDev.VerifyReboot()
}

func (d DeltaRootfsInstaller) RollbackReboot() error {
	return d.realDev.RollbackReboot()
}

func (d DeltaRootfsInstaller) VerifyRollbackReboot() error {
	return d.realDev.VerifyRollbackReboot()
}

func (d DeltaRootfsInstaller) Failure() error {
	return d.realDev.Failure()
}

func (d DeltaRootfsInstaller) Cleanup() error {
	return d.realDev.Cleanup()
}

func (d DeltaRootfsInstaller) GetType() string {
	return d.realDev.GetType()
}

func (d DeltaRootfsInstaller) NewUpdateStorer(updateType *string, payloadNum int) (handlers.UpdateStorer, error) {
	return d, nil
}

func (d DeltaRootfsInstaller) GetInactive() (string, error) {
	return d.realDev.GetInactive()
}

func (d DeltaRootfsInstaller) GetActive() (string, error) {
	return d.realDev.GetActive()
}
