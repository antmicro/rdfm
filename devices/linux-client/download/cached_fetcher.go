package download

import (
	"os"
	"io"
	"crypto/sha1"

	"github.com/antmicro/rdfm/parser"

	"github.com/mendersoftware/mender/client"
	log "github.com/sirupsen/logrus"
)

type ReadSaver struct {
	data                []byte
	offset              int
}

type CombinedSourceReader struct {
	firstReader         io.Reader
	firstReaderEOF      bool
	secondReader        io.Reader
}

func (u *ReadSaver) Write(p []byte) (n int, err error) {
	u.data = append(u.data, p...)
	return len(p), nil
}

func (u *ReadSaver) Read(p []byte) (n int, err error) {
	if u.offset >= len(u.data) {
		return 0, io.EOF
	}
	if cap(p) <= len(u.data) - u.offset {
		n = cap(p)
	} else {
		n = len(u.data) - u.offset
	}
	for i, val := range u.data[u.offset:u.offset + n] {
		p[i] = val
	}
	u.offset += n
	return n, nil
}

func (c *CombinedSourceReader) Read(p []byte) (n int, err error) {
	if !c.firstReaderEOF {
		n, err = c.firstReader.Read(p)
		c.firstReaderEOF = (err == io.EOF)
		return n, nil
	}
	return c.secondReader.Read(p)
}

func CacheArtifactFromURI(url string, cacheDirectory string,
	clientConfig client.Config) (string, error) {

	log.Infof("Starting artifact download from %s", url)

	apiReq, _ := client.NewApiClient(clientConfig)
	image, _, err := client.NewUpdate().FetchUpdate(apiReq, url, 0)
	defer image.Close()

	if err != nil {
		return "", err
	}

	urlReader := &ReadSaver {offset: 0}
	readSplitter := io.TeeReader(image, urlReader)

	bytes, err := parser.GetHeader(readSplitter)
	headerHash := sha1.Sum(bytes)

	log.Infof("Header hash: %x", headerHash)

	doubleReader := &CombinedSourceReader {
		firstReader: urlReader,
		firstReaderEOF: false,
		secondReader: image,
	}

	file, err := os.CreateTemp(cacheDirectory, "update.cache-")
	defer file.Close()

	if err != nil {
		return "", err
	}

	data := make([]byte, 4096)
	var wholeSize int64
	for {
		n, err := doubleReader.Read(data)
		wholeSize += int64(n)
		file.Write(data[:n])
		if err == io.EOF {
			break
		}
		if err != nil {
			return file.Name(), err
		}
	}

	return file.Name(), nil
}
