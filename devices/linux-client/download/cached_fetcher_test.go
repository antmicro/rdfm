package download

import (
	"bytes"
	"github.com/stretchr/testify/assert"
	"io"
	"testing"
)

var FirstTestData = []byte{0x60, 0x09, 0x20, 0x01, 0x30, 0x07}
var SecondTestData = []byte{0x04, 0x00, 0x02, 0x66}

type BufferCloser struct {
	*bytes.Buffer
}

func (b *BufferCloser) Close() error { return nil }

func TestReadSaver(t *testing.T) {
	readSaver := &ReadSaver{offset: 0}
	readSaver.Write(FirstTestData)

	readBackBuffer, err := readNBytes(readSaver, len(FirstTestData))

	assert.NoError(t, err)
	assert.Equal(t, FirstTestData, readBackBuffer)
}

func TestCombinedSourceReader(t *testing.T) {
	firstDataReader := &BufferCloser{bytes.NewBuffer(FirstTestData)}
	secondDataReader := &BufferCloser{bytes.NewBuffer(SecondTestData)}

	combinedSourceReader := &CombinedSourceReader{
		firstReader:    firstDataReader,
		firstReaderEOF: false,
		secondReader:   secondDataReader,
	}

	readBackBuffer, err := readNBytes(combinedSourceReader, len(FirstTestData)+len(SecondTestData))

	assert.NoError(t, err)
	assert.Equal(t, append(FirstTestData, SecondTestData...), readBackBuffer)
}

func TestTeeReadCloser(t *testing.T) {
	readBackBuffer := bytes.NewBuffer([]byte{})
	firstDataReader := &BufferCloser{bytes.NewBuffer(FirstTestData)}
	dataWriter := &BufferCloser{readBackBuffer}

	teeReadCloser := &TeeReadCloser{
		reader: firstDataReader,
		writer: dataWriter,
	}

	_, err := readNBytes(teeReadCloser, len(FirstTestData))
	assert.NoError(t, err)
	assert.Equal(t, FirstTestData, readBackBuffer.Bytes())
}

func readNBytes(reader io.Reader, length int) ([]byte, error) {
	var err error
	readBackBuffer := make([]byte, length)
	bytesRead := 0
	for {
		n, err := reader.Read(readBackBuffer[bytesRead:])
		bytesRead += n
		if bytesRead >= length || err != nil {
			break
		}
	}
	return readBackBuffer, err
}
