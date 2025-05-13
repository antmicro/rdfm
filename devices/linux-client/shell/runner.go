package shell

import (
	"errors"
	"sync"

	"golang.org/x/sync/semaphore"
)

// Keeps track of shell processes spawned by the daemon.
type ShellRunner struct {
	shellCount *semaphore.Weighted      // Current available shell count.
	sessions   map[string]*ShellSession // Dict of all currently running shells.
	mut        sync.Mutex               // Protects sessions dict.
}

var (
	ErrSessionNotFound     = errors.New("session not found")
	ErrSessionLimitReached = errors.New("session limit reached")
)

// Create a new shell runner that is capable of spawning up to limit concurrent
// shell processes.
func NewShellRunner(limit int) (*ShellRunner, error) {
	sr := new(ShellRunner)
	sr.shellCount = semaphore.NewWeighted(int64(limit))
	sr.sessions = make(map[string]*ShellSession)
	return sr, nil
}

// Spawn a new shell process and associate it with a given UUID.
func (s *ShellRunner) Spawn(uuid string) (*ShellSession, error) {
	ok := s.shellCount.TryAcquire(1)
	if !ok {
		return nil, ErrSessionLimitReached
	}

	session, err := NewShellSession(uuid)
	if err != nil {
		return nil, err
	}

	s.mut.Lock()
	defer s.mut.Unlock()
	s.sessions[uuid] = session

	return session, nil
}

// Terminate a shell session that was previously spawned. The associated shell
// process is terminated if it is still running.
func (s *ShellRunner) Terminate(uuid string) error {
	s.mut.Lock()
	defer s.mut.Unlock()

	v, ok := s.sessions[uuid]
	if !ok {
		return ErrSessionNotFound
	}
	v.Close()
	delete(s.sessions, uuid)
	s.shellCount.Release(1)

	return nil
}
