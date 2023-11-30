package netUtils

import (
	"errors"
	"log"
	"net"
	"regexp"

	"github.com/gorilla/websocket"
)

func AddrWithoutPort(addr string) (string, error) {
	re1 := regexp.MustCompile(`((\d+\.?)+)[:/].*?`)
	result := re1.FindStringSubmatch(addr)
	if len(result) < 2 {
		return "", errors.New("Not a valid IPv4 addr")
	}
	return result[1], nil
}

func ConnectedMacAddr(conn *websocket.Conn) (string, error) {
	connIp, err := AddrWithoutPort(conn.LocalAddr().String())
	if err != nil {
		return "", err
	}

	interfaces, _ := net.Interfaces()
	for _, inter := range interfaces {
		if addrs, err := inter.Addrs(); err == nil {
			for _, addr := range addrs {
				interfaceIp, err := AddrWithoutPort(addr.String())
				if err != nil {
					return "", err
				}
				if interfaceIp == connIp {
					log.Println("Found:", interfaceIp, connIp)
					if inter.HardwareAddr.String() == "" {
						return "loopback", nil
					}
					return inter.HardwareAddr.String(), nil
				}
			}
		}
	}
	return "", errors.New("No matching interface found")
}
