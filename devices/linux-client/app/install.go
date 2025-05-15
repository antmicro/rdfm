package app

import (
	"encoding/json"
	"io"
	"io/ioutil"
	"strings"

	"github.com/pkg/errors"

	"github.com/antmicro/rdfm/devices/linux-client/download"
	"github.com/antmicro/rdfm/devices/linux-client/handlers"
	"github.com/antmicro/rdfm/devices/linux-client/parser"

	"github.com/mendersoftware/mender/client"
	"github.com/mendersoftware/mender/datastore"
	dev "github.com/mendersoftware/mender/device"
	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/store"
	"github.com/mendersoftware/mender/utils"

	log "github.com/sirupsen/logrus"
)

const (
	errMsgDependencyNotSatisfiedF = "Artifact dependency %q not satisfied by currently installed artifact (%v != %v)."
	errMsgInvalidDependsTypeF     = "invalid type %T for dependency with name %s"
)

func DoInstall(device *dev.DeviceManager, updateURI string,
	clientConfig client.Config, rebootExitCode bool) error {

	var image io.ReadCloser
	var imageSize int64
	var err error

	if strings.HasPrefix(updateURI, "http:") ||
		strings.HasPrefix(updateURI, "https:") {

		log.Infof("Start updating from URI: [%s]", updateURI)
		image, imageSize, err = download.FetchAndCacheUpdateFromURI(updateURI, clientConfig)
	} else {
		log.Infof("Start updating from local image file: [%s]", updateURI)
		image, imageSize, err = installer.FetchUpdateFromFile(updateURI)
	}
	if err != nil {
		return err
	}

	p := utils.NewProgressWriter(imageSize)
	tr := io.TeeReader(image, p)

	err = DoInstallStates(ioutil.NopCloser(tr), device, rebootExitCode)

	if err == nil {
		download.CleanCache()
	}

	return err
}

func DoInstallStates(art io.ReadCloser,
	device *dev.DeviceManager, rebootExitCode bool) error {

	installHandler, err := parser.InitializeArtifactHandlers(art, &device.InstallerFactories)

	if err != nil {
		return err
	}

	currentProvides, err := datastore.LoadProvides(device.Store)
	// inject our RDFM “provides” so Mender will see that the device supports xdelta/rsync
	currentProvides["rdfm.software.supports_rsync"] = "true"
	currentProvides["rdfm.software.supports_xdelta"] = "true"

	err = installHandler.VerifyDependencies(currentProvides)

	if err != nil {
		return err
	}

	err = installHandler.StorePayloads()
	if err != nil {
		log.Errorf("Download failed: %s", err.Error())
		handleFailure(installHandler)
		return err
	}

	err = installHandler.InstallUpdate()
	if err != nil {
		handleFailure(installHandler)
		return err
	}

	installHandler.SaveUpdateToStore(device.Store)

	if installHandler.IsRollbackSupported() {
		log.Infof("Use 'commit' to update, or 'rollback' to roll back the update.")
	} else {
		log.Infof("Artifact doesn't support rollback. Committing immediately.")
		installHandler.Commit()
	}

	if installHandler.IsRebootNeeded() {
		log.Infof("At least one payload requested a reboot of the device it updated.")
	}

	return nil
}

func DoCommit(device *dev.DeviceManager) error {
	log.Infof("Committing Artifact...")
	stateData, installers, err := restoreHandlerData(device)
	if err != nil {
		return err
	}
	for _, inst := range installers {
		inst.CommitUpdate()
	}
	err = storeUpdateInDB(stateData, device)

	return err
}

func DoRollback(device *dev.DeviceManager) error {
	log.Infof("Rolling back Artifact...")
	stateData, installers, err := restoreHandlerData(device)
	if err != nil {
		return err
	}
	for _, inst := range installers {
		if support, _ := inst.SupportsRollback(); support {
			inst.Rollback()
		}
	}
	stateData.ArtifactName = ""
	err = storeUpdateInDB(stateData, device)

	return err
}

func storeUpdateInDB(stateData *datastore.StandaloneStateData, device *dev.DeviceManager) error {
	err := device.Store.WriteTransaction(func(txn store.Transaction) error {
		err := txn.Remove(datastore.StandaloneStateKey)
		if err != nil {
			return err
		}
		if stateData.ArtifactName != "" {
			return datastore.CommitArtifactData(txn, stateData.ArtifactName,
				stateData.ArtifactGroup, stateData.ArtifactTypeInfoProvides,
				stateData.ArtifactClearsProvides)
		}
		return nil
	})
	return err
}

func restoreHandlerData(device *dev.DeviceManager) (*datastore.StandaloneStateData, []installer.PayloadUpdatePerformer, error) {

	data, err := device.Store.ReadAll(datastore.StandaloneStateKey)
	if err != nil {
		return nil, nil, err
	}
	var stateData datastore.StandaloneStateData
	err = json.Unmarshal(data, &stateData)
	if err != nil {
		return nil, nil, err
	}

	if stateData.Version != datastore.StandaloneStateDataVersion {
		return &stateData, nil, errors.New("Incompatible version stored in database.")
	}

	installHandlers, err := handlers.RestoreHandlersFromStore(&device.InstallerFactories, device.Store, stateData.PayloadTypes)

	return &stateData, installHandlers, err
}

func handleFailure(installHandler *handlers.Handler) {
	if installHandler.IsRollbackSupported() {
		installHandler.Rollback()
	}
	installHandler.Cleanup()
}
