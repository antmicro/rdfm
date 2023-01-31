package app

import (
	"errors"
	"path"

	"github.com/antmicro/rdfm/delta"
	"github.com/antmicro/rdfm/helpers"
	"github.com/mendersoftware/mender/app"
	"github.com/mendersoftware/mender/client"
	"github.com/mendersoftware/mender/conf"
	"github.com/mendersoftware/mender/datastore"
	"github.com/mendersoftware/mender/device"
	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/store"
	"github.com/mendersoftware/mender/system"
	log "github.com/sirupsen/logrus"
)

type RDFM struct {
	menderConfig  *conf.MenderConfig
	store         *store.DBStore
	deviceManager *device.DeviceManager
}

func NewRdfmContext() (*RDFM, error) {
	menderConfig, err := loadMenderConfig()
	if err != nil {
		return nil, err
	}

	store, err := loadMenderDbStore()
	if err != nil {
		return nil, err
	}

	deviceManager, err := createMenderDeviceManager(menderConfig, store)
	if err != nil {
		return nil, err
	}

	ctx := RDFM{
		menderConfig:  menderConfig,
		store:         store,
		deviceManager: deviceManager,
	}
	return &ctx, nil
}

func loadMenderConfig() (*conf.MenderConfig, error) {
	menderConfig, err := conf.LoadConfig(conf.DefaultConfFile, conf.DefaultFallbackConfFile)
	if err != nil {
		return nil, errors.New("failed to load configuration from file")
	}

	if menderConfig.MenderConfigFromFile.DeviceTypeFile != "" {
		menderConfig.DeviceTypeFile = menderConfig.MenderConfigFromFile.DeviceTypeFile
	} else {
		menderConfig.MenderConfigFromFile.DeviceTypeFile = path.Join(conf.DefaultDataStore, "device_type")
		menderConfig.DeviceTypeFile = path.Join(conf.DefaultDataStore, "device_type")
	}
	return menderConfig, nil
}

// Checks whether the database is initialized by looking at the stored provides
func isDbStoreInitialized(store *store.DBStore) bool {
	provides, err := datastore.LoadProvides(store)
	if err != nil {
		log.Debug("Provides could not be loaded - database uninitialized")
		return false
	}

	// If no provides are present, we assume that the database is uninitialized,
	// i.e this is the first boot into a system image.
	if len(provides) > 0 {
		log.Debug("Database is already initialized", provides)
		return true
	}

	log.Debug("Missing provides - database uninitialized")
	return false
}

// Reinitializes the client database
// The contents of 'artifact_info' and 'provides_info' files in the default config
// directory are used to reinitialize the default artifact_name and the provides of
// the currently installed artifact. If reading these files fails, the artifact_name
// is initialized to 'unknown'.
func reinitializeDbStore(s *store.DBStore) (*store.DBStore, error) {
	var data map[string]string
	var err error

	log.Debug("Reinitializing database")

	artifactName := "unknown"
	data, err = helpers.LoadKeyValueFile(path.Join(conf.GetConfDirPath(), "artifact_info"))
	if err == nil && data["artifact_name"] != "" {
		artifactName = data["artifact_name"]
		log.Debug("Reinitializing artifact_name from artifact_info: ", artifactName)
	}

	provides := make(map[string]string)
	data, err = helpers.LoadKeyValueFile(path.Join(conf.GetConfDirPath(), "provides_info"))
	if err == nil {
		if data["artifact_name"] != "" {
			log.Warn("provides_info file contained artifact_name - this is not allowed, ignoring")
			delete(data, "artifact_name")
		}

		provides = data
		log.Debug("Reinitializing provides from provides_info: ", provides)
	}

	err = s.WriteTransaction(func(txn store.Transaction) error {
		return datastore.CommitArtifactData(txn, artifactName, "unknown", provides, nil)
	})

	if err != nil {
		return nil, errors.New("database initialization failed")
	}
	return s, nil
}

func loadMenderDbStore() (*store.DBStore, error) {
	store := store.NewDBStore(conf.DefaultDataStore)
	if store == nil {
		return nil, errors.New("failed to load DB store")
	}

	if isDbStoreInitialized(store) {
		return store, nil
	}

	return reinitializeDbStore(store)
}

func createMenderDeviceManager(menderConfig *conf.MenderConfig, store *store.DBStore) (*device.DeviceManager, error) {
	bootEnv := installer.NewEnvironment(new(system.OsCalls), menderConfig.BootUtilitiesSetActivePart, menderConfig.BootUtilitiesGetNextActivePart)

	dualRootFsDevice := installer.NewDualRootfsDevice(bootEnv, new(system.OsCalls), menderConfig.GetDeviceConfig())
	if dualRootFsDevice == nil {
		return nil, errors.New("config does not contain partition definitions")
	}

	deltaInstaller := delta.NewDeltaInstaller(dualRootFsDevice)
	dm := device.NewDeviceManager(deltaInstaller, menderConfig, store)
	return dm, nil
}

// Install an artifact at the given path
// This can be either an artifact on the local filesystem, or an HTTP URL
func (ctx *RDFM) InstallArtifact(path string) error {
	clientConfig := client.Config{}
	stateExec := device.NewStateScriptExecutor(ctx.menderConfig)

	return app.DoStandaloneInstall(ctx.deviceManager, path, clientConfig, stateExec, false)
}

// Attempt to commit the currently installed update
func (ctx *RDFM) CommitCurrentArtifact() error {
	stateExec := device.NewStateScriptExecutor(ctx.menderConfig)

	return app.DoStandaloneCommit(ctx.deviceManager, stateExec)
}

// Attempt to rollback the currently installed update
func (ctx *RDFM) RollbackCurrentArtifact() error {
	stateExec := device.NewStateScriptExecutor(ctx.menderConfig)

	return app.DoStandaloneRollback(ctx.deviceManager, stateExec)
}

func (ctx *RDFM) GetCurrentArtifactName() (string, error) {
	return ctx.deviceManager.GetCurrentArtifactName()
}

func (ctx *RDFM) GetCurrentArtifactProvides() (map[string]string, error) {
	return ctx.deviceManager.GetProvides()
}
