package device

import (
	"crypto"
	crand "crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"log/slog"
	"os"
	"path"
)

type DeviceKey struct {
	rsa *rsa.PrivateKey
}

// Initializes the device key.
// The the key already exists, it will be loaded
// otherwise this function will generate a new
// private key and save it for future use.
func InitDeviceKey(keyPath string, log *slog.Logger) (*DeviceKey, error) {
	kLog := log.With(slog.String("key", keyPath))

	info, err := os.Stat(keyPath)
	if err != nil {
		if !errors.Is(err, os.ErrNotExist) {
			return nil, err
		}

		// Key doesn't exist - generate new one
		kLog.Debug("Device key not found. Generating new one")
		rsa, err := rsa.GenerateKey(crand.Reader, 3072)
		if err != nil {
			return nil, err
		}

		// Save it for future use
		if err := os.MkdirAll(path.Dir(keyPath), 0700); err != nil {
			return nil, err
		}
		f, err := os.OpenFile(keyPath, os.O_WRONLY|os.O_CREATE, 0600)
		if err != nil {
			return nil, err
		}
		defer f.Close()

		if err := pem.Encode(f, &pem.Block{
			Type:  "PRIVATE KEY",
			Bytes: x509.MarshalPKCS1PrivateKey(rsa),
		}); err != nil {
			return nil, err
		}

		return &DeviceKey{rsa}, nil
	}

	// Only owner should have (at most) Read or Read/Write permissions to private key
	if mode := info.Mode(); mode.Perm()&0077 != 0 {
		kLog.Warn("Private device key is accessible to other users")
	}

	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, err
	}

	kLog.Debug("Using existing device key")

	pemBlock, _ := pem.Decode(keyBytes)

	if rsa, err := x509.ParsePKCS1PrivateKey(pemBlock.Bytes); err == nil {
		return &DeviceKey{rsa}, nil
	}

	key, err := x509.ParsePKCS8PrivateKey(pemBlock.Bytes)
	if err == nil {
		if rsa, ok := key.(*rsa.PrivateKey); ok {
			return &DeviceKey{rsa}, nil
		}
	}

	return nil, errors.New("Unsupported key type")
}

func (dk *DeviceKey) PubKeyPEM() string {
	keyBytes := pem.EncodeToMemory(&pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: x509.MarshalPKCS1PublicKey(&dk.rsa.PublicKey),
	})

	return string(keyBytes)
}

func (dk *DeviceKey) SignPayload(data []byte) ([]byte, error) {
	dataHash := sha256.Sum256(data)

	return rsa.SignPKCS1v15(crand.Reader, dk.rsa, crypto.SHA256, dataHash[:])
}
