package app

import (
	"io"
	"io/ioutil"
	"strings"

	"github.com/antmicro/rdfm/download"

	"github.com/mendersoftware/mender/app"
	"github.com/mendersoftware/mender/client"
	dev "github.com/mendersoftware/mender/device"
	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/statescript"
	"github.com/mendersoftware/mender/utils"
	log "github.com/sirupsen/logrus"
)

func DoInstall(device *dev.DeviceManager, updateURI string,
	clientConfig client.Config,
	stateExec statescript.Executor, rebootExitCode bool) error {

	var image io.ReadCloser
	var imageSize int64
	var err error

	if strings.HasPrefix(updateURI, "http:") ||
		strings.HasPrefix(updateURI, "https:") {

		log.Infof("Start updating from URI: [%s]", updateURI)
		image, imageSize, err = download.FetchAndCacheUpdateFromURI(updateURI, clientConfig)
	} else {
		log.Infof("Start updating from local image file: [%s]", updateURI)
		image, imageSize, err = installer.FetchUpdateFromFile(updateURI)
	}
	if err != nil {
		return err
	}

	p := utils.NewProgressWriter(imageSize)
	tr := io.TeeReader(image, p)

	err = app.DoStandaloneInstallStates(ioutil.NopCloser(tr), device, stateExec, rebootExitCode)

	if err == nil {
		download.CleanCache()
	}

	return err
}
