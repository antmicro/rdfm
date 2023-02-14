package main

import (
	"fmt"
	"io"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/handlers"
)

const (
	deltaUpdateType = "rootfs-image"
)

type DeltaComposer struct {
	handlers.Composer

	rootfsComposer handlers.Composer
}

func NewDeltaComposer(rootfsComposer handlers.Composer) DeltaComposer {
	return DeltaComposer{
		rootfsComposer: rootfsComposer,
	}
}

func (d *DeltaComposer) GetVersion() int {
	return 3
}

// Return type of this update, which could be augmented.
func (d *DeltaComposer) GetUpdateType() *string {
	t := deltaUpdateType
	return &t
}

// Return type of original (non-augmented) update, if any.
func (d *DeltaComposer) GetUpdateOriginalType() *string {
	return nil
}

// /
// Returns merged data of non-augmented and augmented data, where the
// latter overrides the former. Returns error if they cannot be merged.
// /
func (d *DeltaComposer) GetUpdateDepends() (artifact.TypeInfoDepends, error) {
	return d.rootfsComposer.GetUpdateDepends()
}

func (d *DeltaComposer) GetUpdateProvides() (artifact.TypeInfoProvides, error) {
	return d.rootfsComposer.GetUpdateProvides()
}

func (d *DeltaComposer) GetUpdateMetaData() (map[string]interface{}, error) {
	return d.rootfsComposer.GetUpdateMetaData()
}

func (d *DeltaComposer) GetUpdateClearsProvides() []string {
	return d.rootfsComposer.GetUpdateClearsProvides()
}

// /
// Returns non-augmented (original) data.
// /
func (d *DeltaComposer) GetUpdateOriginalDepends() artifact.TypeInfoDepends {
	return d.rootfsComposer.GetUpdateOriginalDepends()
}

func (d *DeltaComposer) GetUpdateOriginalProvides() artifact.TypeInfoProvides {
	return d.rootfsComposer.GetUpdateOriginalProvides()
}

func (d *DeltaComposer) GetUpdateOriginalMetaData() map[string]interface{} {
	return d.rootfsComposer.GetUpdateOriginalMetaData()
}

func (d *DeltaComposer) GetUpdateOriginalClearsProvides() []string {
	return d.rootfsComposer.GetUpdateOriginalClearsProvides()
}

// /
// Operates on non-augmented files.
// /
func (d *DeltaComposer) GetUpdateFiles() [](*handlers.DataFile) {
	f := d.rootfsComposer.GetUpdateFiles()
	for k, v := range f {
		fmt.Println("GetUpdateFiles called", k, v)
	}
	return f
}

func (d *DeltaComposer) SetUpdateFiles(files [](*handlers.DataFile)) error {
	fmt.Println("SetUpdateFiles called", files)
	return d.rootfsComposer.SetUpdateFiles(files)
}

// /
// Gets both augmented and non-augmented files.
// /
func (d *DeltaComposer) GetUpdateAllFiles() [](*handlers.DataFile) {
	f := d.rootfsComposer.GetUpdateAllFiles()
	for k, v := range f {
		fmt.Println("GetUpdateAllFiles called", k, v)
	}
	return f
}

func (d *DeltaComposer) ComposeHeader(args *handlers.ComposeHeaderArgs) error {
	return d.rootfsComposer.ComposeHeader(args)
}

// The interface stubs below operate on augment artifacts
// These are not necessary for implementing deltas, so null them out
// https://github.com/mendersoftware/mender/blob/master/Documentation/update-modules-v3-file-api.md#signatures-and-augmented-artifacts

// /
// Returns augmented data.
// /
func (d *DeltaComposer) GetUpdateAugmentDepends() artifact.TypeInfoDepends {
	return nil
}

func (d *DeltaComposer) GetUpdateAugmentProvides() artifact.TypeInfoProvides {
	return nil
}

func (d *DeltaComposer) GetUpdateAugmentMetaData() map[string]interface{} {
	return nil
}

func (d *DeltaComposer) GetUpdateAugmentClearsProvides() []string {
	return nil
}

func (d *DeltaComposer) GetUpdateOriginalTypeInfoWriter() io.Writer {
	return nil
}

func (d *DeltaComposer) GetUpdateAugmentTypeInfoWriter() io.Writer {
	return nil
}

// /
// Operates on augmented files.
// /
func (d *DeltaComposer) GetUpdateAugmentFiles() [](*handlers.DataFile) {
	return nil
}

func (d *DeltaComposer) SetUpdateAugmentFiles(files [](*handlers.DataFile)) error {
	return nil
}
