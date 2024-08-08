package telemetry

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"time"
)

type SizeLimitWriter struct {
	filePath string
	maxSize  uint64
	maxFiles uint64
	fp       *os.File
	closed   bool
}

func MakeSizeLimitWriter(filePath string, maxSize uint64, maxFiles uint64) (*SizeLimitWriter, error) {
	fp, err := os.OpenFile(filePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return nil, err
	}

	w := SizeLimitWriter{filePath: filePath, maxSize: maxSize, maxFiles: maxFiles, fp: fp}
	return &w, nil
}

func (w *SizeLimitWriter) Write(output []byte) (int, error) {
	// If .Closed() was called, do nothing
	if w.closed {
		return 0, errors.New(".Close() was already called")
	}

	//  Check if the buffer size is smaller than max filesize
	if uint64(len(output)) > w.maxSize {
		return 0, errors.New("input buffer larger than the maximum size of the log file")
	}

	// Check if file is too big to fit the new buffer, if yes then rotate
	fi, err := w.fp.Stat()
	if err != nil {
		return 0, err
	}
	if uint64(fi.Size()) + uint64(len(output)) > w.maxSize {
		if w.fp, err = rotate(w.fp, w.filePath, w.maxFiles); err != nil {
			return 0, err
		}
	}

	// Do the write
	n, err := w.fp.Write(output)
	return n, err
}

func (w *SizeLimitWriter) Close() {
	w.fp.Close()
	w.closed = true
}

func rotate(fp *os.File, filePath string, maxFiles uint64) (*os.File, error) {
	// Close the current file
	if fp != nil {
		err := fp.Close()
		fp = nil
		if err != nil {
			return fp, err
		}
	}

	// Rename the old file to be concatenated with Unix epoch
	_, err := os.Stat(filePath)
	if err == nil {
		err = os.Rename(filePath, filePath+"."+fmt.Sprintf("%d", time.Now().Unix()))
		if err != nil {
			return fp, err
		}
	}

	// List the files in the log directory
	dir := filepath.Dir(filePath)
	entries, err := os.ReadDir(filepath.Dir(dir))
	if err != nil {
		return fp, nil
	}

	// Regexp to match log filename with Unix epoch
	re := regexp.MustCompile(regexp.QuoteMeta(filepath.Base(filePath)) + `\.[0-9]+`)

	// Remove all that don't match + directories
	i := 0
	for _, e := range entries {
		s := e.Name()
		fi, _ := os.Stat(dir + "/" + s)
		if !fi.IsDir() && re.MatchString(s) {
			entries[i] = e
			i++
		}
	}
	for j := i; j < len(entries); j++ {
		entries[j] = nil
	}
	entries = entries[:i]

	// Sort and remove old ones if there's too many of them
	if uint64(len(entries)) >= maxFiles {
		sort.Slice(entries, func(i, j int) bool {
			return entries[i].Name() < entries[j].Name()
		})
		for i := 0; uint64(i) != uint64(len(entries))-maxFiles+1; i++ {
			os.Remove(dir + "/" + entries[i].Name())
		}
	}

	// Create a new file for writing and return
	fp, err = os.OpenFile(filePath, os.O_CREATE|os.O_WRONLY, 0644)
	return fp, err
}
