package netUtils

import (
	"errors"
	"log"
	"net"
	"regexp"
)

const SERVER_URL_PATTERN = "http(s)://127.0.0.1:5000"

var urlMatchError = errors.New("Couldn't match the server URL with the pattern of: '" + SERVER_URL_PATTERN + "'")

func AddrWithOrWithoutPort(addr string, withPort bool) (string, error) {
	pattern := `(?:\d+\.){3}\d+`
	if withPort {
		pattern = pattern + `:\d+`
	}
	re := regexp.MustCompile(pattern)
	result := re.FindStringSubmatch(addr)
	if len(result) < 1 {
		return "", urlMatchError
	}
	return result[0], nil
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
		return "", errors.New("Failed to get MAC address from a valid interface")
	}
	return "", errors.New("Failed to get MAC address")
}
