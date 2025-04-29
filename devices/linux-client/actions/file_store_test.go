package actions

import (
	"context"
	"encoding/binary"
	"os"
	"path"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

const (
	TestFileStoreCapacity = 100
)

var (
	TestPattern = []byte{0x00, 0x11, 0x22, 0x33}
)

func intToBytes(value int) []byte {
	bs := make([]byte, 8)
	binary.LittleEndian.PutUint64(bs, uint64(value))
	return bs
}

func testFileStoreCreation(t *testing.T, len int) {
	fs, err := NewFileStore(t.TempDir(), len)
	assert.Nil(t, err)
	assert.NotNil(t, fs)
}

func discoverItems(storeDirectory string) map[string][]byte {
	items := make(map[string][]byte)
	itemsPath := path.Join(storeDirectory, "items")
	files, err := os.ReadDir(itemsPath)
	if err != nil {
		return items
	}

	for _, file := range files {
		data, err := os.ReadFile(path.Join(itemsPath, file.Name()))
		if err == nil {
			items[file.Name()] = data
		}
	}
	return items
}

func TestFileStoreCreation32(t *testing.T) {
	testFileStoreCreation(t, 32)
}

func TestFileStoreCreation512(t *testing.T) {
	testFileStoreCreation(t, 512)
}

func TestFileStoreCreation1024(t *testing.T) {
	testFileStoreCreation(t, 1024)
}

func TestNonBlockingEnqueue(t *testing.T) {
	store := t.TempDir()
	fs, _ := NewFileStore(store, TestFileStoreCapacity)

	err := fs.TryEnqueue(TestPattern)
	assert.Nil(t, err)
	items := discoverItems(store)
	assert.Equal(t, len(items), 1)

	err = fs.TryEnqueue(TestPattern)
	assert.Nil(t, err)
	items = discoverItems(store)
	assert.Equal(t, len(items), 2)
}

func TestNonBlockingEnqueuePastCapacity(t *testing.T) {
	store := t.TempDir()
	fs, _ := NewFileStore(store, TestFileStoreCapacity)

	for i := 0; i < TestFileStoreCapacity; i++ {
		err := fs.TryEnqueue(TestPattern)
		assert.Nil(t, err)
	}
	err := fs.TryEnqueue(TestPattern)
	assert.Equal(t, err, ErrorStoreFull)

	// No additional items should be created in the filesystem.
	items := discoverItems(store)
	assert.Equal(t, len(items), TestFileStoreCapacity)
}

func TestNonBlockingDequeue(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	err := fs.TryEnqueue(TestPattern)
	assert.Nil(t, err)

	item, err := fs.TryDequeue()
	assert.Nil(t, err)
	assert.NotNil(t, item)
	assert.Equal(t, FileBlob(TestPattern), item)
}

func TestNonBlockingDequeueEmpty(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)
	item, err := fs.TryDequeue()
	assert.Nil(t, item)
	assert.Equal(t, err, ErrorStoreEmpty)
}

func TestPeekEmpty(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)
	item := fs.Peek()
	assert.Nil(t, item)
}

func TestPopEmpty(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)
	err := fs.Pop()
	assert.NotNil(t, err)
	assert.Equal(t, err, ErrorStoreEmpty)
}

func TestNonBlockingEnqueueAndDequeueOrder(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	// Enqueue incrementing integers starting from 0.
	for i := 0; i < TestFileStoreCapacity; i++ {
		err := fs.TryEnqueue(intToBytes(i))
		assert.Nil(t, err)
	}

	// Reading back from the file store should give the exact same ordering to
	// fulfill queue semantics.
	for i := 0; i < TestFileStoreCapacity; i++ {
		item, err := fs.TryDequeue()
		assert.Nil(t, err)
		assert.NotNil(t, item)

		expected := intToBytes(i)
		assert.Equal(t, item, FileBlob(expected))
	}
}

func TestBlockingEnqueueAndDequeueOrder(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var wg sync.WaitGroup

	go func() {
		defer wg.Done()
		// Enqueue incrementing integers starting from 0.
		for i := 0; i < TestFileStoreCapacity; i++ {
			err := fs.Enqueue(intToBytes(i), ctx)
			assert.Nil(t, err)
		}
	}()
	wg.Add(1)

	go func() {
		defer wg.Done()
		// Reading back from the file store should give the exact same ordering to
		// fulfill queue semantics.
		for i := 0; i < TestFileStoreCapacity; i++ {
			item, err := fs.Dequeue(ctx)
			assert.Nil(t, err)
			assert.NotNil(t, item)

			expected := intToBytes(i)
			assert.Equal(t, item, FileBlob(expected))
		}
	}()
	wg.Add(1)

	wg.Wait()
}

func TestBlockingDequeue(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	var wg sync.WaitGroup
	go func() {
		defer wg.Done()
		fetched, err := fs.Dequeue(context.Background())
		assert.Nil(t, err)
		assert.Equal(t, fetched, FileBlob(TestPattern))
	}()
	wg.Add(1)

	go func() {
		defer wg.Done()
		err := fs.TryEnqueue(TestPattern)
		assert.Nil(t, err)
	}()
	wg.Add(1)

	wg.Wait()
}

func TestBlockingDequeueCancel(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	ctx, cancel := context.WithCancel(context.Background())

	var wg sync.WaitGroup
	go func() {
		defer wg.Done()

		_, err := fs.Dequeue(ctx)
		assert.NotNil(t, err)
	}()
	wg.Add(1)

	time.Sleep(1 * time.Second)
	cancel()

	wg.Wait()
}

func TestBlockingEnqueue(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	var wg sync.WaitGroup

	for i := 0; i < TestFileStoreCapacity; i++ {
		err := fs.TryEnqueue(TestPattern)
		assert.Nil(t, err)
	}

	// Producer goroutine, will block immediately on start.
	go func() {
		defer wg.Done()

		err := fs.Enqueue(TestPattern, context.Background())
		assert.Nil(t, err)
	}()
	wg.Add(1)

	// Consumer goroutine.
	go func() {
		defer wg.Done()

		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
		defer cancel()

		dequeuedCount := 0
		for {
			item, err := fs.Dequeue(ctx)
			if err != nil {
				break
			}
			dequeuedCount += 1
			assert.Equal(t, item, FileBlob(TestPattern))
		}
		assert.Equal(t, dequeuedCount, TestFileStoreCapacity+1)
	}()
	wg.Add(1)

	wg.Wait()
}

func TestBlockingEnqueueCancel(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	for i := 0; i < TestFileStoreCapacity; i++ {
		err := fs.TryEnqueue(TestPattern)
		assert.Nil(t, err)
	}

	ctx, cancel := context.WithCancel(context.Background())

	var wg sync.WaitGroup
	go func() {
		defer wg.Done()

		// Enqueue will block, as the queue is full.
		err := fs.Enqueue(TestPattern, ctx)
		assert.NotNil(t, err)
	}()
	wg.Add(1)

	time.Sleep(1 * time.Second)
	cancel()

	wg.Wait()
}

func TestDequeueFromDiskLoadedData(t *testing.T) {
	dir := t.TempDir()
	// Enqueue something to the filestore, dir will be populated with the
	// enqueued item.
	fs, _ := NewFileStore(dir, TestFileStoreCapacity)
	err := fs.TryEnqueue(TestPattern)
	assert.Nil(t, err)

	// Load the same persistence directory using a different filestore to
	// simulate a restart. The item should be visible.
	reloadedFs, _ := NewFileStore(dir, TestFileStoreCapacity)
	item, err := reloadedFs.TryDequeue()
	assert.Nil(t, err)
	assert.Equal(t, item, FileBlob(TestPattern))
	// detail: make sure we're not overinitializing the semaphore counter.
	item, err = reloadedFs.TryDequeue()
	assert.NotNil(t, err)
}

func TestWaitNonEmpty(t *testing.T) {
	fs, _ := NewFileStore(t.TempDir(), TestFileStoreCapacity)

	var wg sync.WaitGroup

	ctx, _ := context.WithTimeout(context.Background(), 1*time.Second)
	wg.Add(1)
	go func() {
		defer wg.Done()
		err := fs.WaitNonEmpty(ctx)
		assert.Nil(t, err)
	}()
	err := fs.TryEnqueue(TestPattern)
	assert.Nil(t, err)

	wg.Wait()
}
