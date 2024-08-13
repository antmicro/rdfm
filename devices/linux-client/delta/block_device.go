package delta

import (
	"bufio"
	"bytes"
	"errors"
	"io"
	"os"
	"strings"
	"syscall"

	log "github.com/sirupsen/logrus"

	"github.com/mendersoftware/mender/system"
)

const MAXIMUM_CHUNK_SIZE = 1 * 1024 * 1024 // 1MB

// Wrapper for block devices that enables optimized writing
type BlockDevice struct {
	Path   string             // Device path, ex. /dev/mmcblk0p1
	writer *blockDeviceWriter // Implementation of WriteCloser + Sync
}

type partition string

func (p partition) mountPoint() string {
	file, err := os.OpenFile("/proc/self/mounts", os.O_RDONLY, 0)
	if err != nil {
		return ""
	}
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		fstab_entry := strings.Fields(scanner.Text())
		label, mountPoint := fstab_entry[0], fstab_entry[1]
		if label == string(p) {
			return mountPoint
		}
	}
	return ""
}

func (p partition) Unmount() error {
	mountPoint := p.mountPoint()
	if mountPoint != "" {
		log.Printf("Partition %s is mounted at %s\n", string(p), mountPoint)
		log.Printf("Unmounting partition %s...\n", string(p))
		err := syscall.Unmount(mountPoint, 0)
		if err != nil {
			return err
		}
	}
	log.Printf("Partition %s unmounted\n", string(p))
	return nil
}

func Open(deviceFile string, updateSize int64) (*BlockDevice, error) {
	// Checks size of update, ensures that device is unmounted, and writes update to it
	log.Printf("Installing update of size %d to %q\n", updateSize, deviceFile)
	if updateSize < 0 {
		return nil, errors.New("invalid update: negative size")
	}

	err := partition(deviceFile).Unmount()
	if err != nil {
		return nil, err
	}

	flags := os.O_RDWR
	log.Printf("Opening device %q with flags: %d\n", deviceFile, flags)

	// Actually open device for writing
	device, err := os.OpenFile(deviceFile, flags, 0)
	if err != nil {
		log.Printf("Error opening device %q:, %v\n", deviceFile, err)
		return nil, err
	}
	// Delegate writing to blockDeviceWriter
	writer, err := initWriter(device, updateSize)
	if err != nil {
		return nil, err
	}
	blockDevice := &BlockDevice{
		Path:   deviceFile,
		writer: writer,
	}
	return blockDevice, nil
}

func (bd *BlockDevice) Write(b []byte) (int, error) {
	// Wrapper delegating writing to blockDeviceWriter
	if bd.writer == nil {
		return 0, errors.New("device not found")
	}
	return bd.writer.Write(b)
}

func (bd *BlockDevice) Close() error {
	if bd.writer != nil {
		return bd.writer.Close()
	}
	return nil
}

func (bd *BlockDevice) Sync() error {
	return bd.writer.Sync()
}

// Optimized WriteCloser + Sync implementation
type blockDeviceWriter struct {
	bytesToUpdate int64

	buffer *bytes.Buffer

	sectorSize int
	frameSize  int

	// Counters for checking how many frames were dirty
	framesChecked     int
	framesOverwritten int

	// If we write more than sectorSize num of bytes perform Sync()
	bytesUntilFlush int

	deviceFile *os.File
}

func initWriter(deviceFile *os.File, updateSize int64) (*blockDeviceWriter, error) {
	sectorSize, err := system.GetBlockDeviceSectorSize(deviceFile)
	if err != nil {
		log.Println("Error initializing device writer, couldn't get sector size of device", err)
		return nil, err
	}
	frameSize := calculateFrameSize(sectorSize)
	log.Printf("Initialized block device writer (sector size: %d, frame size: %d)\n",
		sectorSize, frameSize)
	return &blockDeviceWriter{
		bytesToUpdate:     updateSize,
		buffer:            bytes.NewBuffer(nil),
		sectorSize:        sectorSize,
		frameSize:         frameSize,
		framesChecked:     0,
		framesOverwritten: 0,
		deviceFile:        deviceFile,
	}, nil
}

func (bdw *blockDeviceWriter) Write(b []byte) (int, error) {
	// Write no more than size of artifact to install
	if bdw.deviceFile == nil {
		return 0, syscall.EBADF
	}

	var noSpace bool = false
	if len(b) > int(bdw.bytesToUpdate) {
		b = b[:bdw.bytesToUpdate]
		noSpace = true
	}
	bytesWritten, err := bdw.bufferedWrite(b)
	if err != nil && noSpace {
		err = syscall.ENOSPC
	}
	bdw.bytesToUpdate -= int64(bytesWritten)
	return bytesWritten, err
}

func (bdw *blockDeviceWriter) Sync() error {
	// Sync() device and reset sync-checking counter
	bdw.bytesUntilFlush = bdw.sectorSize
	return bdw.deviceFile.Sync()
}

func (bdw *blockDeviceWriter) Close() error {
	// Flush remaining bytes from buf and sync device before closing it
	_, err := bdw.writeFrameIfDiff(bdw.buffer.Bytes())
	if err != nil {
		log.Println("Error writing remaining bytes in Close(), ", err)
	}
	err = bdw.Sync()
	if err != nil {
		log.Println("Error syncing device in Close(), ", err)
		return err
	}
	return bdw.deviceFile.Close()
}

func (bdw *blockDeviceWriter) bufferedWrite(b []byte) (int, error) {
	// Write data to frame-sized buffer until it's full
	bytesBuffered, err := bdw.buffer.Write(b)
	if bdw.buffer.Len() < int(bdw.frameSize) || err != nil {
		return bytesBuffered, err
	}

	framesToWrite := bdw.buffer.Len() / int(bdw.frameSize)
	for ; framesToWrite > 0; framesToWrite-- {
		_, err = bdw.writeFrameIfDiff(bdw.buffer.Next(bdw.frameSize))
		if err != nil {
			return 0, err
		}
	}
	return len(b), nil
}

func (bdw *blockDeviceWriter) cmpFrames(b []byte) (bool, error) {
	// Check if frame needs to be updated
	deviceFrame := make([]byte, bdw.frameSize)
	_, err := io.ReadFull(bdw.deviceFile, deviceFrame)
	if err != nil {
		log.Printf("Error reading frame (size: %d)\n", len(b))
	}

	return !bytes.Equal(b, deviceFrame), err
}

func (bdw *blockDeviceWriter) writeFrameIfDiff(b []byte) (int, error) {
	// Write update but only if frame differs
	blocksDiff, err := bdw.cmpFrames(b)
	if err != nil {
		return 0, err
	}

	bdw.framesChecked++
	if blocksDiff {
		_, err = bdw.deviceFile.Seek(-int64(bdw.frameSize), io.SeekCurrent)
		if err != nil {
			log.Println("Error seeking back frame: ", err)
			return 0, err
		}

		bytesWritten, err := bdw.writeAndSyncIfNeeded(b)
		bdw.framesOverwritten++
		return bytesWritten, err
	}
	return int(bdw.frameSize), err
}

func (bdw *blockDeviceWriter) writeAndSyncIfNeeded(b []byte) (int, error) {
	// Sync() should be performed every time we write more than sector size
	bytesWritten, err := bdw.deviceFile.Write(b)
	bdw.bytesUntilFlush -= bytesWritten
	if bdw.bytesUntilFlush < 0 && err == nil {
		return bytesWritten, bdw.Sync()
	} else if err != nil {
		return bytesWritten, err
	}
	return bytesWritten, err
}

func calculateFrameSize(sectorSize int) int {
	frameSize := sectorSize
	for frameSize < MAXIMUM_CHUNK_SIZE {
		frameSize *= 2
	}
	return frameSize
}
