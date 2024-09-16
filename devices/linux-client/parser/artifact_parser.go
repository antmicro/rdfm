package parser

import (
	"archive/tar"
	"errors"
	"io"

	"github.com/antmicro/rdfm/handlers"

	"github.com/mendersoftware/mender-artifact/areader"
	mhandlers "github.com/mendersoftware/mender-artifact/handlers"
	"github.com/mendersoftware/mender/installer"
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
			offset := 0
			for {
				if offset >= len(header) {
					break
				}
				n, _ := tarReader.Read(header[offset:])
				offset += n
			}
			return header, nil
		}
	}

	return nil, errors.New("no header found in artifact")
}

func InitializeArtifactHandlers(art io.ReadCloser, inst *installer.AllModules) (*handlers.Handler, error) {
	ar := areader.NewReader(art)

	rootfs := mhandlers.NewRootfsInstaller()
	rootfs.SetUpdateStorerProducer(inst.DualRootfs)
	ar.RegisterHandler(rootfs)

	for _, newHandler := range handlers.AvailableHandlers {
		err := ar.RegisterHandler(newHandler())
		if err != nil {
			return nil, err
		}
	}

	ar.ForbidUnknownHandlers = true

	if err := ar.ReadArtifactHeaders(); err != nil {
		return nil, err
	}

	return handlers.NewHandler(ar), nil
}
