package download

import (
	"crypto/sha1"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/antmicro/rdfm/devices/linux-client/conf"
	"github.com/antmicro/rdfm/devices/linux-client/parser"

	"github.com/mendersoftware/mender/client"
	log "github.com/sirupsen/logrus"
)

type ReadSaver struct {
	data   []byte
	offset int
}

type CombinedSourceReader struct {
	firstReader    io.ReadCloser
	firstReaderEOF bool
	secondReader   io.ReadCloser
}

type TeeReadCloser struct {
	reader io.ReadCloser
	writer io.WriteCloser
}

func (u *ReadSaver) Write(p []byte) (n int, err error) {
	u.data = append(u.data, p...)
	return len(p), nil
}

func (u *ReadSaver) Read(p []byte) (n int, err error) {
	if u.offset >= len(u.data) {
		return 0, io.EOF
	}
	if len(p) <= len(u.data)-u.offset {
		n = len(p)
	} else {
		n = len(u.data) - u.offset
	}
	copy(p, u.data[u.offset:u.offset+n])
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

func (t *TeeReadCloser) Read(p []byte) (n int, err error) {
	n, err = t.reader.Read(p)
	t.writer.Write(p[:n])
	return n, err
}

func (t *TeeReadCloser) Close() error {
	t.reader.Close()
	t.writer.Close()
	return nil
}

func FetchAndCacheUpdateFromURI(url string, clientConfig client.Config) (io.ReadCloser, int64, error) {

	rdfmConf, _, _ := conf.GetConfig()
	image, imageSize, supportsRangeRequests, err := NewRdfmHttpUpdateReader(url, 0, clientConfig)

	if err != nil {
		return nil, 0, err
	}

	if !supportsRangeRequests || !rdfmConf.HttpCacheEnabled {
		log.Warnf("Caching disabled")
		return image, imageSize, nil
	}

	readSaver := &ReadSaver{
		offset: 0,
	}
	readSplitter := io.TeeReader(image, readSaver)

	bytes, err := parser.GetHeader(readSplitter)
	headerHash := sha1.Sum(bytes)

	if _, err := os.Stat(conf.RdfmCachePath); os.IsNotExist(err) {
		os.MkdirAll(conf.RdfmCachePath, os.ModePerm)
	}
	cacheFile := filepath.Join(conf.RdfmCachePath, fmt.Sprintf(strings.Replace(conf.RdfmCacheFilePattern, "*", "%x", 1), headerHash))

	var doubleReader *CombinedSourceReader
	var file *os.File

	if stat, err := os.Stat(cacheFile); err == nil {
		image.Close()
		log.Infof("Resuming download from cache")
		image, _, _, err := NewRdfmHttpUpdateReader(url, stat.Size(), clientConfig)
		if err != nil {
			return nil, 0, err
		}
		file, err = os.OpenFile(cacheFile, os.O_APPEND|os.O_RDWR, stat.Mode())
		tr := &TeeReadCloser{image, file}
		doubleReader = &CombinedSourceReader{
			firstReader:    file,
			firstReaderEOF: false,
			secondReader:   tr,
		}
		return doubleReader, imageSize, nil
	}

	file, err = os.Create(cacheFile)
	doubleReader = &CombinedSourceReader{
		firstReader:    readSaver,
		firstReaderEOF: false,
		secondReader:   image,
	}

	updateCacher := &TeeReadCloser{
		reader: doubleReader,
		writer: file,
	}

	if err != nil {
		return nil, 0, err
	}

	return updateCacher, imageSize, nil
}

func CleanCache() {
	log.Infof("Removing cached updates")
	_, err := os.Stat(conf.RdfmCachePath)
	if err != nil {
		log.Warnf("Cache directory doesn't exist - nothing to clean")
		return
	}
	files, err := filepath.Glob(filepath.Join(conf.RdfmCachePath, conf.RdfmCacheFilePattern))
	for _, file := range files {
		if err := os.Remove(file); err != nil {
			log.Warnf("Could not remove %s", file)
		}
	}
}
