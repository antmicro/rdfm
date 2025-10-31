package conf

import (
	"bufio"
	"encoding/json"
	"errors"
	"io/ioutil"
	"os"
	"reflect"

	log "github.com/sirupsen/logrus"

	"github.com/mendersoftware/mender/conf"
)

const DEFAULT_UPDATE_POLL_INTERVAL_S = 15 * 60
const DEFAULT_RETRY_POLL_INTERVAL_S = 60
const DEFAULT_HTTP_CACHE_ENABLED = true
const DEFAULT_RECONNECT_RETRY_COUNT = 3
const DEFAULT_RECONNECT_RETRY_TIME = 60

// The following regex provides a sane default for matching the network
// interface to use for fetching the unique device identifier. This will try to
// match:
//  1. unpredictable naming schemes, e.g eth0
//  2. PCI-based network devices using slot and path naming, e.g ens9f0/enp33s0f0
//  3. onboard naming scheme, e.g eno1
//
// See below reference on predictable naming:
// https://www.freedesktop.org/software/systemd/man/latest/systemd.net-naming-scheme.html
const DEFAULT_MAC_ADDRESS_IF_REGEXP = "eth\\d+|en(([Pp]\\d+)*(s\\d+)+(f\\d+)*(n\\d+|d\\d+)*|([o]\\d+))"
const DEFAULT_TELEMETRY_ENABLE = false
const DEFAULT_TELEMETRY_BATCH_SIZE = 1024
const DEFAULT_SHELL_ENABLE = true
const DEFAULT_SHELL_CONCURRENT_MAX_COUNT = 5
const DEFAULT_ACTION_ENABLE = true
const DEFAULT_ACTION_QUEUE_SIZE = 32
const DEFAULT_FILESYSTEM_ENABLE = true
const DEFAULT_FILESYSTEM_BASE_DIR = "/"
const DEFAULT_VERIFICATION_SCRIPT_PATH = ""

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
	// Regular expression used for picking the netif to use as MAC address source
	MacAddressInterfaceRegex string `json:",omitempty"`

	// Is telemetry enabled. Default: false
	TelemetryEnable bool `json:",omitempty"`
	// Maximum size of logs in bytes that the client will batch. Default: 1024
	TelemetryBatchSize int32 `json:",omitempty"`
	// Log levels from within the client to be captured
	TelemetryLogLevel string `json:",omitempty"`
	// Broker addresses
	TelemetryBootstrapServers string `json:",omitempty"`

	// Is shell support enabled? Default: true
	ShellEnable bool `json:",omitempty"`
	// Maximum amount of concurrent shells. Default: 5
	ShellConcurrentMaxCount int `json:",omitempty"`
	// Path to shell. If not set, $SHELL or default shell path list will be used.
	ShellPath string `json:",omitempty"`

	// Is action support enabled? Default: true
	ActionEnable bool `json:",omitempty"`
	// Incoming/outgoing action queue size. Default: 32
	ActionQueueSize int `json:",omitempty"`

	// Is filesystem support enabled? Default: true
	FileSystemEnable bool `json:",omitempty"`

	// Base directory for filesystem access. Default: "/"
	FileSystemBaseDir string `json:",omitempty"`

	// Path to the script used to verify system correctness before commit. Default: ""
	VerificationScriptPath string `json:",omitempty"`
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
		MacAddressInterfaceRegex:  DEFAULT_MAC_ADDRESS_IF_REGEXP,
		TelemetryEnable:           DEFAULT_TELEMETRY_ENABLE,
		TelemetryBatchSize:        DEFAULT_TELEMETRY_BATCH_SIZE,
		ShellEnable:               DEFAULT_SHELL_ENABLE,
		ShellConcurrentMaxCount:   DEFAULT_SHELL_CONCURRENT_MAX_COUNT,
		ActionEnable:              DEFAULT_ACTION_ENABLE,
		ActionQueueSize:           DEFAULT_ACTION_QUEUE_SIZE,
		FileSystemEnable:          DEFAULT_FILESYSTEM_ENABLE,
		FileSystemBaseDir:         DEFAULT_FILESYSTEM_BASE_DIR,
		VerificationScriptPath:    DEFAULT_VERIFICATION_SCRIPT_PATH,
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

func LoadTagsConfig(path string) ([]string, error) {
	if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
		return make([]string, 0), nil
	}

	if err := checkConfigFilePermissions(path); err != nil {
		log.Error("tags: config file: wrong permissions")
		return nil, err
	}

	configFile, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer configFile.Close()

	var config []string

	sc := bufio.NewScanner(configFile)
	for sc.Scan() {
		line := sc.Text()
		config = append(config, line)
	}
	if err = sc.Err(); err != nil {
		return nil, err
	}

	return config, nil
}
