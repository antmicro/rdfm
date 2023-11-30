package netUtils

import (
	"errors"
	"log"
	"net"
	"net/url"
	"regexp"
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
		return "", errors.New("Failed to get MAC address from a valid interface")
	}
	return "", errors.New("Failed to get MAC address")
}
