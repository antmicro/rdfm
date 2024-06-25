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
	firstReader         io.ReadCloser
	firstReaderEOF      bool
	secondReader        io.ReadCloser
}

type UpdateCacher struct {
	reader              io.ReadCloser
	cacheFile           *os.File
}

func (u *ReadSaver) Write(p []byte) (n int, err error) {
	u.data = append(u.data, p...)
	return len(p), nil
}

func (u *ReadSaver) Read(p []byte) (n int, err error) {
	if u.offset >= len(u.data) {
		return 0, io.EOF
	}
	if len(p) <= len(u.data) - u.offset {
		n = len(p)
	} else {
		n = len(u.data) - u.offset
	}
	for i, val := range u.data[u.offset:u.offset + n] {
		p[i] = val
	}
	u.offset += n
	return n, nil
}

func (u *ReadSaver) Close() error {
	return nil
}

func (c *CombinedSourceReader) Read(p []byte) (n int, err error) {
	if !c.firstReaderEOF {
		n, err = c.firstReader.Read(p)
		c.firstReaderEOF = (err == io.EOF)
		return n, nil
	}
	return c.secondReader.Read(p)
}

func (u *CombinedSourceReader) Close() error {
	u.firstReader.Close()
	u.secondReader.Close()
	return nil
}

func (u *UpdateCacher) Read(p []byte) (n int, err error) {
	n, err = u.reader.Read(p)
	u.cacheFile.Write(p[:n])
	return n, err
}

func (u *UpdateCacher) Close() error {
	u.reader.Close()
	u.cacheFile.Close()
	return nil
}

func FetchAndCacheUpdateFromURI(url string, cacheDirectory string,
	clientConfig client.Config) (io.ReadCloser, int64, error) {

	log.Infof("Starting artifact download from %s", url)

	apiReq, _ := client.NewApiClient(clientConfig)
	image, imageSize, err := client.NewUpdate().FetchUpdate(apiReq, url, 0)

	if err != nil {
		return nil, 0, err
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
	updateCacher := &UpdateCacher {
		reader:			doubleReader,
		cacheFile:	file,
	}

	if err != nil {
		return nil, 0, err
	}

	return updateCacher, imageSize, nil
}
