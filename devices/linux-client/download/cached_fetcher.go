package download

import (
	"os"
	"io"

	"github.com/antmicro/rdfm/parser"

	"github.com/mendersoftware/mender/client"
	log "github.com/sirupsen/logrus"
)

func CacheArtifactFromURI(url string, cacheDirectory string,
	clientConfig client.Config) (string, error) {

	log.Infof("Starting artifact download from %s", url)

	apiReq, _ := client.NewApiClient(clientConfig)
	image, imageSize, err := client.NewUpdate().FetchUpdate(apiReq, url, 0)
	defer image.Close()

	if err != nil {
		return "", err
	}

	file, err := os.CreateTemp(cacheDirectory, "update.cache-")
	defer file.Close()

	if err != nil {
		return "", err
	}

	data := make([]byte, 4096)
	var wholeSize int64
	for {
		n, err := image.Read(data)
		if err != nil && err != io.EOF {
			return file.Name(), err
		}
		wholeSize += int64(n)
		file.Write(data[:n])
		if wholeSize >= imageSize {
			break
		}
	}

	return file.Name(), nil
}
