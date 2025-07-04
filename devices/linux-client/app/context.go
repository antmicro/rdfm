package app

import (
	"encoding/json"
	"errors"
	"path"

	conf "github.com/antmicro/rdfm/conf"
	"github.com/antmicro/rdfm/delta"
	"github.com/antmicro/rdfm/helpers"
	"github.com/mendersoftware/mender/client"
	mconf "github.com/mendersoftware/mender/conf"
	"github.com/mendersoftware/mender/datastore"
	"github.com/mendersoftware/mender/device"
	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/store"
	"github.com/mendersoftware/mender/system"
	log "github.com/sirupsen/logrus"
)

type RDFM struct {
	RdfmConfig          *conf.RDFMConfig
	menderConfig        *mconf.MenderConfig
	RdfmTelemetryConfig *map[string]conf.RDFMLoggerConfiguration
	RdfmActionsConfig   *[]conf.RDFMActionsConfiguration
	store               *store.DBStore
	deviceManager       *device.DeviceManager
}

// overlay mender config with shared rdfm config fields and return it
func OverlayMenderConfig(rdfmConfig *conf.RDFMConfig, menderConfig *mconf.MenderConfig) (*mconf.MenderConfig, error) {
	fromRdfm, err := json.Marshal(rdfmConfig.ToMenderConfig())
	if err != nil {
		log.Println("Error casting and serializing RDFMConf: ", err)
		return nil, err
	}
	if err := json.Unmarshal(fromRdfm, &menderConfig); err != nil {
		log.Println("Error overlaying MenderConf with RDFMConf: ", err)
		return nil, err
	}
	return menderConfig, nil
}

func NewRdfmContext() (*RDFM, error) {
	rdfmConfig, menderConfig, err := loadConfig()
	if err != nil {
		return nil, err
	}

	menderConfig, err = OverlayMenderConfig(rdfmConfig, menderConfig)
	if err != nil {
		return nil, err
	}

	rdfmTelemetryConfig, err := conf.LoadTelemetryConfig(conf.RdfmDefaultLoggersPath)
	if err != nil {
		return nil, err
	}

	rdfmActionsConfig, err := conf.LoadActionsConfig(conf.RdfmDefaultActionsPath)
	if err != nil {
		return nil, err
	}

	store, err := loadDbStore()
	if err != nil {
		return nil, err
	}

	deviceManager, err := createDeviceManager(menderConfig, store)
	if err != nil {
		return nil, err
	}

	ctx := RDFM{
		rdfmConfig,
		menderConfig,
		rdfmTelemetryConfig,
		rdfmActionsConfig,
		store,
		deviceManager,
	}
	return &ctx, nil
}

func loadConfig() (*conf.RDFMConfig, *mconf.MenderConfig, error) {
	RDFMConfig, MenderConfig, err := conf.LoadConfig(conf.RdfmDefaultConfigPath, conf.RdfmOverlayConfigPath)
	if err != nil {
		return nil, nil, errors.New("failed to load configuration from file")
	}
	if MenderConfig.DeviceTypeFile == "" {
		deviceTypeFile := path.Join(conf.RdfmDataDirectory, "device_type")
		RDFMConfig.DeviceTypeFile = deviceTypeFile
	}

	return RDFMConfig, MenderConfig, nil
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
	data, err = helpers.LoadKeyValueFile(conf.RdfmArtifactInfoPath)
	if err == nil && data["artifact_name"] != "" {
		artifactName = data["artifact_name"]
		log.Debug("Reinitializing artifact_name from artifact_info: ", artifactName)
	}

	provides := make(map[string]string)
	data, err = helpers.LoadKeyValueFile(conf.RdfmProvidesInfoPath)
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

func loadDbStore() (*store.DBStore, error) {
	store := store.NewDBStore(conf.RdfmDataDirectory)
	if store == nil {
		return nil, errors.New("failed to load DB store")
	}

	if isDbStoreInitialized(store) {
		return store, nil
	}

	return reinitializeDbStore(store)
}

func createDeviceManager(config *mconf.MenderConfig, store *store.DBStore) (*device.DeviceManager, error) {
	bootEnv := installer.NewEnvironment(new(system.OsCalls), config.BootUtilitiesSetActivePart, config.BootUtilitiesGetNextActivePart)

	dualRootFsDevice := installer.NewDualRootfsDevice(bootEnv, new(system.OsCalls), config.GetDeviceConfig())
	if dualRootFsDevice == nil {
		return nil, errors.New("config does not contain partition definitions")
	}

	deltaInstaller := delta.NewDeltaInstaller(dualRootFsDevice)
	dm := device.NewDeviceManager(deltaInstaller, config, store)
	return dm, nil
}

// Install an artifact at the given path
// This can be either an artifact on the local filesystem, or an HTTP URL
func (ctx *RDFM) InstallArtifact(path string) error {
	clientConfig := client.Config{}

	return DoInstall(ctx.deviceManager, path, clientConfig, false)
}

// Attempt to commit the currently installed update
func (ctx *RDFM) CommitCurrentArtifact() error {
	return DoCommit(ctx.deviceManager)
}

// Attempt to rollback the currently installed update
func (ctx *RDFM) RollbackCurrentArtifact() error {
	return DoRollback(ctx.deviceManager)
}

func (ctx *RDFM) GetCurrentArtifactName() (string, error) {
	return ctx.deviceManager.GetCurrentArtifactName()
}

func (ctx *RDFM) GetCurrentDeviceType() (string, error) {
	return ctx.deviceManager.GetDeviceType()
}

func (ctx *RDFM) GetCurrentArtifactProvides() (map[string]string, error) {
	return ctx.deviceManager.GetProvides()
}
