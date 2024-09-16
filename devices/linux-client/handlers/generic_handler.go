package handlers

import (
	"io"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/handlers"
	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/store"
)

type GenericHandler struct {
	installer.PayloadUpdatePerformer
	Type string
}

type StateSaver interface {
	SaveState(store store.Store) error
	RestoreState(store store.Store) error
}

func (g *GenericHandler) GetType() string {
	return g.Type
}

func (s *GenericHandler) GetUpdateType() *string {
	updateType := s.Type
	return &updateType
}

func (s *GenericHandler) ReadHeader(r io.Reader, path string, version int, augmented bool) error {
	return nil
}

func (s *GenericHandler) SetUpdateStorerProducer(producer handlers.UpdateStorerProducer) {

}

func (s *GenericHandler) NewAugmentedInstance(orig handlers.ArtifactUpdate) (handlers.Installer, error) {
	return nil, nil
}

func (s *GenericHandler) GetUpdateFiles() [](*handlers.DataFile) {
	return nil
}

func (s *GenericHandler) SetUpdateFiles(files [](*handlers.DataFile)) error {
	return nil
}

func (s *GenericHandler) GetUpdateAugmentFiles() [](*handlers.DataFile) {
	return nil
}

func (s *GenericHandler) SetUpdateAugmentFiles(files [](*handlers.DataFile)) error {
	return nil
}

func (s *GenericHandler) GetVersion() int {
	return 0
}

func (s *GenericHandler) GetUpdateOriginalType() *string {
	return nil
}

func (s *GenericHandler) GetUpdateDepends() (artifact.TypeInfoDepends, error) {
	return nil, nil
}

func (s *GenericHandler) GetUpdateProvides() (artifact.TypeInfoProvides, error) {
	return nil, nil
}

func (s *GenericHandler) GetUpdateMetaData() (map[string]interface{}, error) {
	return nil, nil
}

func (s *GenericHandler) GetUpdateClearsProvides() []string {
	return nil
}

func (s *GenericHandler) GetUpdateOriginalDepends() artifact.TypeInfoDepends {
	return nil
}

func (s *GenericHandler) GetUpdateOriginalProvides() artifact.TypeInfoProvides {
	return nil
}

func (s *GenericHandler) GetUpdateOriginalMetaData() map[string]interface{} {
	return nil
}

func (s *GenericHandler) GetUpdateOriginalClearsProvides() []string {
	return nil
}

func (s *GenericHandler) GetUpdateAugmentDepends() artifact.TypeInfoDepends {
	return nil
}

func (s *GenericHandler) GetUpdateAugmentProvides() artifact.TypeInfoProvides {
	return nil
}

func (s *GenericHandler) GetUpdateAugmentMetaData() map[string]interface{} {
	return nil
}

func (s *GenericHandler) GetUpdateAugmentClearsProvides() []string {
	return nil
}

func (s *GenericHandler) GetUpdateOriginalTypeInfoWriter() io.Writer {
	return nil
}

func (s *GenericHandler) GetUpdateAugmentTypeInfoWriter() io.Writer {
	return nil
}

func (s *GenericHandler) VerifyReboot() error {
	return nil
}

func (s *GenericHandler) RollbackReboot() error {
	return nil
}

func (s *GenericHandler) VerifyRollbackReboot() error {
	return nil
}

func (s *GenericHandler) Failure() error {
	return nil
}

func (s *GenericHandler) Cleanup() error {
	return nil
}
