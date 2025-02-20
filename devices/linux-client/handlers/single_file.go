package handlers

import (
	"encoding/json"
	"io"
	"os"
	"path"
	"strconv"
	"strings"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"

	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/store"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/handlers"
)

type SingleFileData struct {
	DestDirectory    string
	Filename         string
	Permissions      os.FileMode
	RollbackFileName string
	RollbackSupport  bool
}

type SingleFileUpdater struct {
	StateSaver
	GenericHandler
	SingleFileData
}

const (
	DestinationDirectory   = "dest_dir"
	PermissionsFile        = "permissions"
	FilenameFile           = "filename"
	RollbackSupportFile    = "rollback_support"
	SingleFileDataStoreKey = "single-file-data-store"
)

func NewSingleFileUpdater() handlers.Installer {
	return &SingleFileUpdater{
		GenericHandler: GenericHandler{Type: "single-file"},
	}
}

func (s *SingleFileUpdater) NewInstance() handlers.Installer {
	return NewSingleFileUpdater()
}

func (s *SingleFileUpdater) NewUpdateStorer(updateType *string, payloadNum int) (handlers.UpdateStorer, error) {
	return s, nil
}

func (s *SingleFileUpdater) Initialize(artifactHeaders,
	artifactAugmentedHeaders artifact.HeaderInfoer,
	payloadHeaders handlers.ArtifactUpdateHeaders) error {
	return nil
}

func (s *SingleFileUpdater) GetUpdateAllFiles() [](*handlers.DataFile) {
	return [](*handlers.DataFile){
		&handlers.DataFile{Name: DestinationDirectory},
		&handlers.DataFile{Name: FilenameFile},
		&handlers.DataFile{Name: PermissionsFile},
		&handlers.DataFile{Name: RollbackSupportFile},
		&handlers.DataFile{Name: s.Filename},
	}
}

func (s *SingleFileUpdater) PrepareStoreUpdate() error {
	return nil
}

func (s *SingleFileUpdater) StoreUpdate(r io.Reader, info os.FileInfo) error {
	switch info.Name() {
	case DestinationDirectory:
		s.DestDirectory = readPayloadFile(r, info.Size())
	case FilenameFile:
		s.Filename = readPayloadFile(r, info.Size())
	case PermissionsFile:
		temp, _ := strconv.ParseInt(readPayloadFile(r, info.Size()), 8, 32)
		s.Permissions = os.FileMode(temp)
	case RollbackSupportFile:
		temp := readPayloadFile(r, info.Size())
		s.RollbackSupport = (temp == "true")
		log.Infof("Rollback: %v", s.RollbackSupport)
	case s.Filename:
		s.updateFile(r)
	}

	return nil
}

func (s *SingleFileUpdater) FinishStoreUpdate() error {
	return nil
}

func (s *SingleFileUpdater) InstallUpdate() error {
	return nil
}

func (s *SingleFileUpdater) NeedsReboot() (installer.RebootAction, error) {
	return installer.NoReboot, nil
}

func (s *SingleFileUpdater) CommitUpdate() error {
	os.Remove(s.RollbackFileName)
	return nil
}

func (s *SingleFileUpdater) SupportsRollback() (bool, error) {
	return s.RollbackSupport, nil
}

func (s *SingleFileUpdater) Rollback() error {
	rollbackFile, _ := os.Open(s.RollbackFileName)
	origFile, _ := os.OpenFile(path.Join(s.DestDirectory, s.Filename), os.O_WRONLY|os.O_CREATE|os.O_TRUNC, s.Permissions)
	defer origFile.Close()

	_, err := io.Copy(origFile, rollbackFile)
	if err != nil {
		return err
	}
	os.Remove(s.RollbackFileName)
	return nil
}

func readPayloadFile(r io.Reader, size int64) string {
	buf := make([]byte, size, size)
	r.Read(buf)
	return strings.TrimSpace(string(buf[:]))
}

func (s *SingleFileUpdater) updateFile(r io.Reader) error {
	// Rollback file
	if s.DestDirectory == "" {
		return errors.New("The destination directory path cannot be empty")
	}

	_, err := os.Stat(s.DestDirectory)
	if os.IsNotExist(err) {
		log.Infof("The destination directory doesn't exist (%s), creating it", s.DestDirectory)
		err = os.MkdirAll(s.DestDirectory, os.ModePerm)
		if err != nil {
			log.Errorf("Could not create destination directory (%s)", s.DestDirectory)
			return err
		}
	}

	if s.RollbackSupport {
		s.RollbackFileName = path.Join(s.DestDirectory, s.Filename+".tmp")
		tempFile, err := os.OpenFile(s.RollbackFileName, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, s.Permissions)
		if err != nil {
			log.Errorf("Could not create or open rollback file (%s)\n", s.RollbackFileName)
			return err
		}
		defer tempFile.Close()
		origFile, err := os.OpenFile(path.Join(s.DestDirectory, s.Filename), os.O_RDONLY, s.Permissions)
		if err == nil {
			io.Copy(tempFile, origFile)
			origFile.Close()
		}
	}
	// Update file
	origFile, err := os.OpenFile(path.Join(s.DestDirectory, s.Filename), os.O_WRONLY|os.O_CREATE|os.O_TRUNC, s.Permissions)
	defer origFile.Close()
	_, err = io.Copy(origFile, r)
	return err
}

func (s *SingleFileUpdater) SaveState(store store.Store) error {
	data, err := json.Marshal(s.SingleFileData)
	if err != nil {
		return err
	}
	return store.WriteAll(SingleFileDataStoreKey, data)
}

func (s *SingleFileUpdater) RestoreState(store store.Store) error {
	data, err := store.ReadAll(SingleFileDataStoreKey)
	if err != nil {
		return err
	}

	err = json.Unmarshal(data, &s.SingleFileData)
	store.Remove(SingleFileDataStoreKey)
	return nil
}

func (s *SingleFileUpdater) GetUpdateClearsProvides() []string {
	return []string{"this-key-cannot-appear-in-provides-80030197597109825875732137944464795696111936699651028614245931085587374788033687"}
}
