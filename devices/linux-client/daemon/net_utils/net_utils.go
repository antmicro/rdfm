package netUtils

import (
	"errors"
	"fmt"
	"io"
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

func ConnectedMacAddr(conn net.Conn) (string, error) {
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

func RecvExactly(s net.Conn, n int) ([]byte, error) {
	buf := make([]byte, 0, n)
	for n > 0 {
		tmp_buf := make([]byte, n)
		bytes_read, err := io.ReadFull(s, tmp_buf)
		if err != nil {
			return nil, fmt.Errorf("socket read error: %w", err)
		}
		buf = append(buf, tmp_buf...)
		n -= bytes_read
	}
	return buf, nil
}
