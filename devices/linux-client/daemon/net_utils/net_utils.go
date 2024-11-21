package netUtils

import (
	"encoding/json"
	"errors"
	"github.com/golang-jwt/jwt/v5"
	"net"
	"net/url"
	"regexp"

	log "github.com/sirupsen/logrus"
)

func HostWithOrWithoutPort(addr string, withPort bool) (string, error) {
	host, err := url.Parse(addr)
	if err != nil {
		return "", err
	}
	if !withPort {
		re := regexp.MustCompile(`:\d+`)
		result := re.Split(host.Host, -1)
		return result[0], nil
	}
	return host.Host, nil
}

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

func GetMacAddr() (string, error) {
	var nifMAC string

	interfaces, err := net.Interfaces()
	if err != nil {
		log.Println("Couldn't get network interface", err)
		return "", err
	} else if len(interfaces) == 0 {
		return "", errors.New("No network interfaces available")
	}
	for _, nif := range interfaces {
		nifMAC = nif.HardwareAddr.String()
		nifName := nif.Name
		nifAddrs, _ := nif.Addrs()
		if nifMAC == "" {
			continue
		}
		for _, a := range nifAddrs {
			ipAddr, _, _ := net.ParseCIDR(a.String())
			if !(ipAddr.IsLoopback() || ipAddr.IsLinkLocalMulticast() || ipAddr.IsLinkLocalUnicast()) {
				log.Println("Using MAC address [ " + nifMAC + " ] from network interface '" + nifName + "' as device identifier")
				return nifMAC, nil
			}
		}
	}
	return "", errors.New("Failed to get MAC address")
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
