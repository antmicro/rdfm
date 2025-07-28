package netUtils

import (
	"encoding/json"
	"errors"
	"net"
	"regexp"
	"sort"
	"time"

	"github.com/antmicro/rdfm/devices/linux-client/conf"
	"github.com/golang-jwt/jwt/v5"

	log "github.com/sirupsen/logrus"
)

var (
	ErrInvalidRegexp       = errors.New("Invalid regular expression")
	ErrNoMatchingInterface = errors.New("No matching interfaces found")
)

var (
	// Cache of the device identifier/MAC address found during call to
	// GetUniqueId.
	cachedDeviceIdentifier *string = nil
)

func ShouldEncryptProxy(addr string) (bool, error) {
	pattern := `http`
	re := regexp.MustCompile(pattern)
	result := re.FindStringSubmatch(addr)
	if len(result) < 1 {
		return false, errors.New("Couldn't match the protocol in server URL - expecting 'http' or 'https'")
	} else {
		pattern = `https`
		re = regexp.MustCompile(pattern)
		result = re.FindStringSubmatch(addr)
		if len(result) > 0 {
			return true, nil
		}
	}
	return false, nil
}

// Return an array of network interfaces sorted by their name.
func getSortedInterfaces() ([]net.Interface, error) {
	interfaces, err := net.Interfaces()
	if err != nil {
		return nil, err
	}
	sort.Slice(interfaces, func(i, j int) bool {
		return interfaces[i].Name < interfaces[j].Name
	})
	return interfaces, nil
}

// Iterate over available network interfaces and find the first non-empty MAC
// address of the interface whose name matches the specified regular expression.
func getMacAddr(pattern string) (string, error) {
	var nifMAC string
	re, err := regexp.Compile(pattern)
	if err != nil {
		return "", ErrInvalidRegexp
	}

	interfaces, err := getSortedInterfaces()
	if err != nil {
		log.Println("Couldn't get network interface", err)
		return "", err
	} else if len(interfaces) == 0 {
		return "", errors.New("No network interfaces available")
	}
	for _, nif := range interfaces {
		nifMAC = nif.HardwareAddr.String()
		nifName := nif.Name
		if nifMAC == "" {
			continue
		}
		if !re.MatchString(nifName) {
			continue
		}
		log.Println("Using MAC address [ " + nifMAC + " ] from network interface '" + nifName + "' as device identifier")
		return nifMAC, nil
	}
	log.Warnln("Failed to find network interface for pattern:", pattern, "that has a MAC address")
	return "", ErrNoMatchingInterface
}

// Get the unique device identifier of this device. This attempts to look for a
// unique value to identify this device with the server using the following
// sources, in order:
//  1. Reading the /var/lib/rdfm/device_id file.
//  2. Querying the MAC address of the network interface matching a regular expression
//     specified in the configuration (MacAddressInterfaceRegex). This value is persisted
//     in device_id once found.
func GetUniqueId() (*string, error) {
	if cachedDeviceIdentifier != nil {
		return cachedDeviceIdentifier, nil
	}

	idFromDeviceInfo, err := conf.LoadDeviceId()
	if err == nil {
		log.Debugln("Using device identifier [", *idFromDeviceInfo, "]", "from config")
		cachedDeviceIdentifier = idFromDeviceInfo
		return cachedDeviceIdentifier, nil
	}

	cfg, _, err := conf.GetConfig()
	if err != nil {
		return nil, errors.New("Failed to get config")
	}
	idFromMacAddr, err := getMacAddr(cfg.MacAddressInterfaceRegex)
	if err == nil {
		// There was no device_id file, save the MAC so future ID queries do not
		// have to enumerate network interfaces again.
		err = conf.SaveDeviceId(idFromMacAddr)
		if err != nil {
			log.Errorln("Failed to save discovered MAC address to file:", err)
		}
		cachedDeviceIdentifier = &idFromMacAddr
		return cachedDeviceIdentifier, nil
	}

	return nil, errors.New("Failed to find unique identifier")
}

type JwtPayload struct {
	DeviceId  string `json:"device_id"`
	CreatedAt int64  `json:"created_at"`
	Expires   int64  `json:"expires"`
}

func ExtractJwtPayload(tokenStr string) (*JwtPayload, error) {
	token, _, err := new(jwt.Parser).ParseUnverified(tokenStr, jwt.MapClaims{})
	if err != nil {
		return nil, err
	}

	if payload, ok := token.Claims.(jwt.MapClaims); ok {
		var payloadStruct JwtPayload
		claimsBytes, err := json.Marshal(payload)
		if err != nil {
			return nil, err
		}
		err = json.Unmarshal(claimsBytes, &payloadStruct)
		if err != nil {
			return nil, err
		}
		return &payloadStruct, nil
	} else {
		return nil, errors.New("Failed to extract JWT payload: false type assertion")
	}
}

type ExpBackoff struct {
	MinDelay     time.Duration
	MaxDelay     time.Duration
	currentDelay time.Duration
	base         float64
}

func NewExpBackoff(minDelay time.Duration, maxDelay time.Duration, base float64) *ExpBackoff {
	if base < 1 {
		return nil
	}

	eb := new(ExpBackoff)
	eb.MinDelay = minDelay
	eb.MaxDelay = maxDelay
	eb.base = base
	eb.Reset()
	return eb
}

func (eb *ExpBackoff) updateDelay() {
	newDelay := time.Duration(float64(eb.currentDelay.Nanoseconds()) * eb.base)
	if eb.MaxDelay < newDelay {
		eb.currentDelay = eb.MaxDelay
	} else {
		eb.currentDelay = newDelay
	}
}

func (eb *ExpBackoff) Retry() time.Duration {
	delay := eb.currentDelay
	eb.updateDelay()
	return delay
}

func (eb *ExpBackoff) Peek() time.Duration {
	return eb.currentDelay
}
func (eb *ExpBackoff) Reset() {
	eb.currentDelay = eb.MinDelay
}
