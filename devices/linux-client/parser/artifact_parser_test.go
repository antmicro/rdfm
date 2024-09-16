package parser

import (
	"archive/tar"
	"bytes"
	"github.com/stretchr/testify/assert"
	"io"
	"testing"
	"time"
)

var TestSlice = []byte{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}

func TestGetCorrectHeader(t *testing.T) {
	reader := getFakeArtifact("header.tar")
	b, err := GetHeader(reader)
	assert.NoError(t, err, "Unexpected artifact header error")
	assert.Equal(t, TestSlice, b, "Incorrect artifact header")
}

func TestGetIncorrectHeader(t *testing.T) {
	reader := getFakeArtifact("no_header_file.txt")
	_, err := GetHeader(reader)
	assert.Error(t, err)
	assert.Contains(t, err.Error(),
		"no header found in artifact")
}

func TestGetNoHeader(t *testing.T) {
	zero_bytes := make([]byte, 10)
	zero_reader := bytes.NewReader(zero_bytes)
	_, err := GetHeader(zero_reader)
	assert.Error(t, err)
	assert.Contains(t, err.Error(),
		"unexpected EOF")
}

func getFakeArtifact(inner_file_name string) io.Reader {
	var buf bytes.Buffer

	tw := tar.NewWriter(&buf)
	hdr := &tar.Header{
		Name:     inner_file_name,
		Size:     int64(len(TestSlice)),
		Mode:     509,
		ModTime:  time.Now(),
		Typeflag: tar.TypeReg,
	}

	tw.WriteHeader(hdr)
	tw.Write(TestSlice)

	return bytes.NewReader(buf.Bytes())
}
