package conf

import (
	"encoding/json"
	"errors"
	"io/ioutil"
	"reflect"

	log "github.com/sirupsen/logrus"

	"github.com/mendersoftware/mender/conf"
)

const DEFAULT_UPDATE_POLL_INTERVAL_S = 15 * 60
const DEFAULT_RETRY_POLL_INTERVAL_S = 60
const DEFAULT_HTTP_CACHE_ENABLED = true
const DEFAULT_RECONNECT_RETRY_COUNT = 3
const DEFAULT_RECONNECT_RETRY_TIME = 60
const DEFAULT_TELEMETRY_ENABLE = false
const DEFAULT_TELEMETRY_BATCH_SIZE = 50

type RDFMConfig struct {
	// Path to the device type file
	DeviceTypeFile string `json:",omitempty"`
	// Path to the overlay config file
	OverlayConfigFile string `json:",omitempty"`

	// Poll interval for checking for new updates
	UpdatePollIntervalSeconds int `json:",omitempty"`

	// Global retry polling max interval for fetching update, authorize wait and update status
	RetryPollIntervalSeconds int `json:",omitempty"`
	// Global max retry poll count
	RetryPollCount int `json:",omitempty"`

	// Path to server SSL certificate
	ServerCertificate string `json:",omitempty"`
	// Server URL (For single server conf)
	ServerURL string `json:",omitempty"`
	// Path to deployment log file
	UpdateLogPath string `json:",omitempty"`
	// Is artifact caching enabled. Default: true
	HttpCacheEnabled bool `json:",omitempty"`
	// HTTP reconnect retry count
	ReconnectRetryCount int `json:",omitempty"`
	// HTTP reconnect retry time
	ReconnectRetryTime int `json:",omitempty"`

	// Is telemetry enabled. Default: false
	TelemetryEnable bool `json:",omitempty"`
	// Number of log entries to be sent at a time. Default: 50
	TelemetryBatchSize int `json:",omitempty"`
}

var rdfmConfigInstance *RDFMConfig
var menderConfigInstance *conf.MenderConfig

func (c RDFMConfig) ToMenderConfig() *conf.MenderConfig {
	menderConfig := conf.NewMenderConfig()

	serialized, err := json.Marshal(c)
	if err != nil {
		log.Panicln("Error serializing RDFMConfig: ", err)
	}

	if err = json.Unmarshal(serialized, &menderConfig); err != nil {
		log.Panicln("Error converting serialized RDFMConfig to MenderConfig: ", err)
	}
	menderConfig.HttpsClient.Certificate = c.ServerCertificate

	return menderConfig
}

func GetConfig() (*RDFMConfig, *conf.MenderConfig, error) {
	if rdfmConfigInstance == nil || menderConfigInstance == nil {
		return LoadConfig(RdfmDefaultConfigPath, RdfmOverlayConfigPath)
	}
	return rdfmConfigInstance, menderConfigInstance, nil
}

// LoadConfig parses the mender and rdfm configuration json-files
// (/etc/rdfm/rdfm.conf - mender conf, /var/lib/rdfm/rdfm.conf - rdfm conf)
// and loads the values into the RDFMConfig structure defining high level
// client configurations.
func LoadConfig(mainConfigFile string, overlayConfigFile string) (*RDFMConfig, *conf.MenderConfig, error) {
	menderConfigInstance := &conf.MenderConfig{}
	rdfmConfigInstance = &RDFMConfig{
		UpdatePollIntervalSeconds: DEFAULT_UPDATE_POLL_INTERVAL_S,
		RetryPollIntervalSeconds:  DEFAULT_RETRY_POLL_INTERVAL_S,
		HttpCacheEnabled:          DEFAULT_HTTP_CACHE_ENABLED,
		ReconnectRetryCount:       DEFAULT_RECONNECT_RETRY_COUNT,
		ReconnectRetryTime:        DEFAULT_RECONNECT_RETRY_TIME,
		TelemetryEnable:           DEFAULT_TELEMETRY_ENABLE,
		TelemetryBatchSize:        DEFAULT_TELEMETRY_BATCH_SIZE,
	}

	// Load Mender config
	loadErr := loadConfigFile(mainConfigFile, menderConfigInstance)
	if loadErr != nil {
		log.Println("Error reading main config:", mainConfigFile)
		log.Println(loadErr)
		return nil, nil, loadErr
	}
	log.Println("Loaded main config", mainConfigFile)
	log.Debugf("Loaded Mender configuration = %#v", menderConfigInstance)

	// Load RDFM config
	loadErr = loadConfigFile(overlayConfigFile, &rdfmConfigInstance)
	if loadErr != nil {
		log.Println("Error reading overlay config:", overlayConfigFile)
		log.Println(loadErr)
		return nil, nil, loadErr
	}
	log.Println("Loaded overlay config", overlayConfigFile)
	log.Debugf("Loaded RDFM configuration = %#v", rdfmConfigInstance)

	return rdfmConfigInstance, menderConfigInstance, nil
}

func loadConfigFile(fileName string, config interface{}) error {
	// Reads rdfm/mender configuration (JSON) file.

	log.Debug("Reading " + reflect.ValueOf(config).String() +
		" configuration from file " + fileName)
	conf, err := ioutil.ReadFile(fileName)
	if err != nil {
		return err
	}

	if err := json.Unmarshal(conf, &config); err != nil {
		switch err.(type) {
		case *json.SyntaxError:
			return errors.New("Error parsing mender configuration file: " + err.Error())
		}
		return errors.New("Error parsing config file: " + err.Error())
	}

	return nil
}
