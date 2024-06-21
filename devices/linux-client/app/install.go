package app

import (
	"io"
	"io/ioutil"
	"os"
	"strings"

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

	var image io.ReadCloser
	var imageSize int64
	var filePath = updateURI
	var upclient client.Updater

	if strings.HasPrefix(updateURI, "http:") ||
		strings.HasPrefix(updateURI, "https:") {
		upclient = client.NewUpdate()

		file, err := os.CreateTemp(RdfmDataDirectory, "update.cache-")
		defer file.Close()

		ac, err := client.NewApiClient(clientConfig)
		image, imageSize, err := upclient.FetchUpdate(ac, updateURI, 0)
		defer image.Close()

		if err != nil {
			return err
		}

		arr := make([]byte, 1024)
		var wholeSize int64
		for {
			n, _ := image.Read(arr)
			wholeSize += int64(n)
			file.Write(arr[:n])
			if wholeSize >= imageSize {
				break
			}
		}

		if err != nil {
			return err
		}
		filePath = file.Name()
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
