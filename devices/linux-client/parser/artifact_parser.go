package parser

import (
	"archive/tar"
	"errors"
	"io"
)

func GetHeader(reader io.Reader) ([]byte, error) {

	tarReader := tar.NewReader(reader)

	for {
		tarFile, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if tarFile.Name == "header.tar" {
			header := make([]byte, tarFile.Size)
			tarReader.Read(header)
			return header, nil
		}
	}

	return nil, errors.New("No header found in artifact")
}
