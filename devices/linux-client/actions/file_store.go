package actions

import (
	"context"
	"errors"
	"io/ioutil"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"sync"

	log "github.com/sirupsen/logrus"
	"golang.org/x/sync/semaphore"
)

type FileBlob []byte

// File-backed item queue. Items are stored as byte blobs.
type FileStore struct {
	rootDir        string              // Base directory path to queue data.
	itemsByIdx     map[int]FileBlob    // In-memory cache of items currently stored on-disk.
	readIdx        int                 // Current read index.
	writeIdx       int                 // Current write index.
	itemsLock      sync.Mutex          // Protects the items map and indexes.
	capacity       int                 // Max items that can be queued.
	availableSlots *semaphore.Weighted // Used as wake-up signal for writers.
	availableItems *semaphore.Weighted // Used as wake-up signal for readers.
}

var (
	ErrorStoreFull           = errors.New("file store is full")
	ErrorStoreEmpty          = errors.New("file store is empty")
	ErrorStoreCannotQueueNil = errors.New("trying to enqueue nil")
)

const (
	DataDirDefaultPerms = 0755
	// Explicitly forbid queue items from being world-readable.
	DataFileDefaultPerms = 0600
)

// Instantiate a FileStore object stored in the directory rootDir with the given
// maximum capacity.
func NewFileStore(rootDir string, capacity int) (*FileStore, error) {
	rootAbs, err := filepath.Abs(rootDir)
	if err != nil {
		return nil, err
	}

	fs := FileStore{
		rootDir:  rootAbs,
		capacity: capacity,
	}

	err = fs.ensureDirs()
	if err != nil {
		return nil, err
	}

	err = fs.Reload()
	if err != nil {
		return nil, err
	}

	return &fs, nil
}

func (q *FileStore) ensureDirs() error {
	err := os.MkdirAll(q.rootDir, DataDirDefaultPerms)
	if err != nil {
		return err
	}

	err = os.MkdirAll(q.itemsPath(), DataDirDefaultPerms)
	if err != nil {
		return err
	}

	return nil
}

func (q *FileStore) pathFromIdx(idx int) string {
	return filepath.Join(q.itemsPath(), strconv.Itoa(idx))
}

func (q *FileStore) idxFromPath(path string) (int, error) {
	basename := filepath.Base(path)
	return strconv.Atoi(basename)
}

func (q *FileStore) itemsPath() string {
	return filepath.Join(q.rootDir, "items")
}

func (q *FileStore) writeFile(idx int, item FileBlob) error {
	itemPath := q.pathFromIdx(idx)

	err := os.WriteFile(itemPath, item, DataFileDefaultPerms)
	if err != nil {
		return err
	}
	return nil
}

func (q *FileStore) readFile(idx int) (FileBlob, error) {
	itemPath := q.pathFromIdx(idx)
	raw, err := os.ReadFile(itemPath)
	if err != nil {
		return nil, err
	}

	return raw, nil
}

func (q *FileStore) removeFile(idx int) error {
	path := q.pathFromIdx(idx)
	err := os.Remove(path)
	if err != nil {
		if !errors.Is(err, os.ErrNotExist) {
			return err
		}
	}
	return nil
}

func (q *FileStore) Reload() error {
	itemsByIdx := make(map[int]FileBlob)
	files, err := ioutil.ReadDir(q.itemsPath())
	if err != nil {
		return err
	}

	for _, file := range files {
		var item FileBlob
		idx, err := q.idxFromPath(file.Name())
		if err != nil {
			log.Warnln("Unparsable file found in FileStore directory:", path.Join(q.rootDir, file.Name()))
			log.Warnln("FileStore may be pointing to a directory containing files not created by it, this is not allowed.")
			continue
		}

		item, err = q.readFile(idx)
		if err != nil {
			return err
		}

		itemsByIdx[idx] = item
	}

	capacity := q.capacity
	if capacity < len(itemsByIdx) {
		capacity = len(itemsByIdx)
	}

	minIdx := -1
	maxIdx := -1

	for idx, _ := range itemsByIdx {
		if minIdx == -1 || idx < minIdx {
			minIdx = idx
		}

		if maxIdx == -1 || idx > maxIdx {
			maxIdx = idx
		}
	}

	// After everything was loaded from the filesystem, we can populate the FileStore.
	// At this point, no errors can happen so we can update the entire object atomically.
	q.itemsLock.Lock()
	defer q.itemsLock.Unlock()

	if minIdx == -1 {
		q.writeIdx = 0
		q.readIdx = 0
	} else {
		q.writeIdx = maxIdx + 1
		q.readIdx = minIdx
	}

	q.itemsByIdx = itemsByIdx
	q.capacity = capacity
	// Set the initial slot count to how many items were loaded from root directory.
	q.availableSlots = semaphore.NewWeighted(int64(q.capacity))
	for range itemsByIdx {
		q.availableSlots.TryAcquire(1)
	}
	// Initially, no items are available, but up to `capacity` can be stored.
	// x/sync semaphores don't support initializing the value of the counter, so
	// in order to initialize the semaphore to match the item count from the
	// filesystem, we first acquire up to `capacity` items and release however
	// many items we've read from storage. End result is that the semaphore's
	// internal counter is properly initialized and dequeuing after restart
	// works as expected.
	q.availableItems = semaphore.NewWeighted(int64(q.capacity))
	for i := 0; i < q.capacity; i++ {
		q.availableItems.TryAcquire(1)
	}
	for range itemsByIdx {
		q.availableItems.Release(1)
	}

	return nil
}

func (q *FileStore) Reset() error {
	err := os.RemoveAll(q.rootDir)
	if err != nil {
		if !errors.Is(err, os.ErrNotExist) {
			return err
		}
	}

	err = q.ensureDirs()
	if err != nil {
		return err
	}

	err = q.Reload()
	if err != nil {
		return err
	}
	return nil
}

func (q *FileStore) getFrontItemIndex() *int {
	if len(q.itemsByIdx) == 0 {
		return nil
	}
	curReadIdx := q.readIdx
	// TODO: This can be done in a non-bruteforce way.
	for {
		var ok bool
		_, ok = q.itemsByIdx[curReadIdx]
		if ok {
			break
		}
		curReadIdx++
	}
	return &curReadIdx
}

func (q *FileStore) pushItemToBack(item FileBlob) error {
	q.itemsLock.Lock()
	defer q.itemsLock.Unlock()

	if item == nil {
		return ErrorStoreCannotQueueNil
	}

	if len(q.itemsByIdx) > q.capacity {
		return ErrorStoreFull
	}

	err := q.writeFile(q.writeIdx, item)
	if err != nil {
		return err
	}
	q.itemsByIdx[q.writeIdx] = item
	q.writeIdx++
	// Inform readers that an item is available.
	q.availableItems.Release(1)

	return nil
}

func (q *FileStore) popFrontItem() FileBlob {
	q.itemsLock.Lock()
	defer q.itemsLock.Unlock()

	frontIdx := q.getFrontItemIndex()
	if frontIdx == nil {
		return nil
	}
	item := q.itemsByIdx[*frontIdx]
	q.removeFile(*frontIdx)
	delete(q.itemsByIdx, *frontIdx)
	q.readIdx = *frontIdx + 1
	// Inform writers that a writeable slot became available.
	q.availableSlots.Release(1)

	return item
}

func (q *FileStore) peekFrontItem() FileBlob {
	q.itemsLock.Lock()
	defer q.itemsLock.Unlock()

	if len(q.itemsByIdx) == 0 {
		return nil
	}
	frontIdx := q.getFrontItemIndex()
	if frontIdx == nil {
		return nil
	}
	return q.itemsByIdx[*frontIdx]
}

// Enqueue an item to the back of the file store, blocking if no space is
// available.
func (q *FileStore) Enqueue(item FileBlob, cancelCtx context.Context) error {
	err := q.availableSlots.Acquire(cancelCtx, 1)
	if err != nil {
		return err
	}
	return q.pushItemToBack(item)
}

// Enqueue an item to the back of the file store, or fail immediately if no
// space is available.
func (q *FileStore) TryEnqueue(item FileBlob) error {
	ok := q.availableSlots.TryAcquire(1)
	if !ok {
		return ErrorStoreFull
	}
	return q.pushItemToBack(item)
}

// Dequeue an item from the front of the queue and return it, blocking if the
// queue is empty.
func (q *FileStore) Dequeue(cancelCtx context.Context) (FileBlob, error) {
	err := q.availableItems.Acquire(cancelCtx, 1)
	if err != nil {
		return nil, err
	}
	return q.popFrontItem(), nil
}

// Dequeue an item from the front of the queue and return it, or fail
// immediately if the queue is empty.
func (q *FileStore) TryDequeue() (FileBlob, error) {
	ok := q.availableItems.TryAcquire(1)
	if !ok {
		return nil, ErrorStoreEmpty
	}
	return q.popFrontItem(), nil
}

// Peek at the front item in the queue without removing it. Returns nil if the
// queue is empty.
func (q *FileStore) Peek() FileBlob {
	return q.peekFrontItem()
}

// Pop the front item from the queue.
func (q *FileStore) Pop() error {
	item := q.popFrontItem()
	if item == nil {
		return ErrorStoreEmpty
	}
	return nil
}

// Block until the queue is non empty. This function can be used in conjunction
// with Peek and Pop.
func (q *FileStore) WaitNonEmpty(cancelCtx context.Context) error {
	return q.availableItems.Acquire(cancelCtx, 1)
}
