package app

import (
	"os"
	"io"
	"io/ioutil"
	"strings"

	"github.com/antmicro/rdfm/download"

	"github.com/mendersoftware/mender/client"
	"github.com/mendersoftware/mender/statescript"
	"github.com/mendersoftware/mender/app"
	"github.com/mendersoftware/mender/utils"
	"github.com/mendersoftware/mender/installer"
	dev "github.com/mendersoftware/mender/device"
	log "github.com/sirupsen/logrus"
)

func DoInstall(device *dev.DeviceManager, updateURI string,
	clientConfig client.Config,
	stateExec statescript.Executor, rebootExitCode bool) error {

	var filePath = updateURI
	var err error

	if strings.HasPrefix(updateURI, "http:") ||
		strings.HasPrefix(updateURI, "https:") {

		filePath, err = download.CacheArtifactFromURI(updateURI, RdfmDataDirectory, clientConfig)

		if err != nil {
			return err
		}
		defer os.Remove(filePath)
	}

	log.Infof("Start updating from local image file: [%s]", filePath)

	image, imageSize, err := installer.FetchUpdateFromFile(filePath)

	if err != nil {
		return err
	}

	p := utils.NewProgressWriter(imageSize)
	tr := io.TeeReader(image, p)

	return app.DoStandaloneInstallStates(ioutil.NopCloser(tr), device, stateExec, rebootExitCode)
}
