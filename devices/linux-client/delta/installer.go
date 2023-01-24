package delta

import (
	"fmt"
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
	log "github.com/sirupsen/logrus"
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

func (d DeltaRootfsInstaller) openActiveForReading() (*os.File, error) {
	activePartition, err := d.realDev.GetActive()
	if err != nil {
		return nil, err
	}
	fmt.Println("Using", activePartition, "as delta base")

	activeDevice, err := os.OpenFile(activePartition, os.O_RDONLY, 0)
	if err != nil {
		return nil, err
	}

	return activeDevice, nil
}

func (d DeltaRootfsInstaller) openInactiveForWriting(imageSize int64) (*block_device.BlockDevice, error) {
	inactivePartition, err := d.realDev.GetInactive()
	if err != nil {
		return nil, err
	}
	fmt.Println("Using", inactivePartition, "as installation target")

	inactiveDevice, err := block_device.BlockDev.Open(inactivePartition, imageSize)
	if err != nil {
		errmsg := "Failed to write the update to the inactive partition: %q"
		return nil, errors.Wrapf(err, errmsg, inactivePartition)
	}

	return inactiveDevice, nil
}

func (d DeltaRootfsInstaller) writeDeltaToInactive(delta io.Reader, inferredImageSize int64) error {
	// Partition the delta is applied on top of
	activePartition, err := d.openActiveForReading()
	if err != nil {
		return err
	}
	defer activePartition.Close()

	// Target partition for the patched base image
	inactivePartition, err := d.openInactiveForWriting(inferredImageSize)
	if err != nil {
		return err
	}

	// Apply the patch
	err = librsync.Patch(activePartition, delta, inactivePartition)
	if err != nil {
		inactivePartition.Close()
		return err
	}

	// Sanity check when calling Close() on the target partition
	// This is to catch any potential errors when syncing.
	err = inactivePartition.Close()
	if err != nil {
		log.Errorf("Failed to close the block-device. Error: %v", err)
		return err
	}

	log.Infof("Wrote %d bytes to the inactive partition", inferredImageSize)
	return nil
}

func (d DeltaRootfsInstaller) storeUpdateDelta(r io.Reader, info os.FileInfo) error {
	// Hacky: the file name for delta signature is some-file-name.1048576.delta,
	// where 1048576 is the original image size.  Artifact installer needs to know
	// the original size for some of its checks.
	deltaSigParts := strings.Split(info.Name(), ".")
	imageSize, err := strconv.ParseInt(deltaSigParts[len(deltaSigParts)-2], 10, 64)
	if err != nil {
		return errors.Wrapf(err, "Unable to infer original image size from delta file name: %s", info.Name())
	}

	return d.writeDeltaToInactive(r, imageSize)
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
	isDelta := strings.HasSuffix(info.Name(), ".delta")
	if isDelta {
		fmt.Println("The artifact is a delta update:", info.Name())
		return d.storeUpdateDelta(r, info)
	}

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
