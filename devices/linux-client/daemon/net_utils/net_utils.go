package netUtils

import (
	"errors"
	"log"
	"net"
	"regexp"
)

func AddrWithoutPort(addr string) (string, error) {
	re1 := regexp.MustCompile(`((\d+\.?)+)[:/].*?`)
	result := re1.FindStringSubmatch(addr)
	if len(result) < 2 {
		return "", errors.New("Not a valid IPv4 addr")
	}
	return result[1], nil
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
