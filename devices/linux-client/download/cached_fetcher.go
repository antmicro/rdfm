package download

import (
	"os"
	"io"
	"fmt"
	"path/filepath"
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
	copy(p, u.data[u.offset:u.offset + n])
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
	n, err = c.secondReader.Read(p)
	return n, err
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

	image, imageSize, supportsRangeRequests, err := NewRdfmHttpUpdateReader(url, 0, clientConfig)

	if err != nil {
		return nil, 0, err
	}

	if !supportsRangeRequests {
		log.Warnf("Server doesn't support range requests - caching disabled")
		return image, imageSize, nil
	}

	readSaver := &ReadSaver{
		offset: 0,
	}
	readSplitter := io.TeeReader(image, readSaver)

	bytes, err := parser.GetHeader(readSplitter)
	headerHash := sha1.Sum(bytes)

	cacheFile := filepath.Join(cacheDirectory, fmt.Sprintf("update-%x.cache", headerHash))

	var doubleReader *CombinedSourceReader
	var file *os.File

	if stat, err := os.Stat(cacheFile); err == nil {
		image.Close()
		log.Infof("Resuming download from cache")
		image, _, _, err := NewRdfmHttpUpdateReader(url, stat.Size(), clientConfig)
		if err != nil {
			return nil, 0, err
		}
		file, err = os.Open(cacheFile)
		doubleReader = &CombinedSourceReader {
			firstReader: file,
			firstReaderEOF: false,
			secondReader: image,
		}
		return doubleReader, imageSize, nil
	}

	file, err = os.Create(cacheFile)
	doubleReader = &CombinedSourceReader{
		firstReader:    readSaver,
		firstReaderEOF: false,
		secondReader:   image,
	}

	updateCacher := &UpdateCacher {
		reader:			doubleReader,
		cacheFile:	file,
	}

	if err != nil {
		return nil, 0, err
	}

	return updateCacher, imageSize, nil
}
