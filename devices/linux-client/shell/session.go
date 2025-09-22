package shell

import (
	"errors"
	"os"
	"os/exec"

	"github.com/antmicro/rdfm/devices/linux-client/serverws"
	"github.com/creack/pty"
	log "github.com/sirupsen/logrus"
	"golang.org/x/sync/errgroup"
)

// Represents an active remote shell process.
type ShellSession struct {
	uuid    string    // ID of the shell session as seen on the server.
	ptmx    *os.File  // Pseudo-terminal associated with the shell.
	command *exec.Cmd // Running process.
}

var (
	// List of well-known shell locations to be considered for spawning a shell.
	// Earlier entries take priority over later ones.
	DefaultShellList = []string{
		"/usr/bin/bash",
		"/bin/bash",
		"/usr/bin/sh",
		"/bin/sh",
	}
	ErrNoShellAvailable = errors.New("no shell found")
)

// Determine the shell executable to use for spawning shell sessions.
func findShell() (*string, error) {
	for _, shellPath := range DefaultShellList {
		_, err := os.Stat(shellPath)
		if err == nil {
			return &shellPath, nil
		}
	}
	return nil, ErrNoShellAvailable
}

// Create a new shell session with the given UUID. This determines the shell
// binary to use and spawns it as a child process of the daemon. To capture
// stdout and provide stdin, call Run with the WebSocket to use for
// communication.
func NewShellSession(uid string) (*ShellSession, error) {
	log.Printf("Creating new shell session with id %s", uid)
	session := new(ShellSession)
	session.uuid = uid
	shell, err := findShell()
	if err != nil {
		return nil, err
	}
	session.command = exec.Command(*shell)
	session.command.Env = append(session.command.Env, "TERM=linux")
	session.command.Env = append(session.command.Env, "LANG=en_US.UTF-8")
	session.command.Env = append(session.command.Env, "XDG_CONFIG_HOME=config")
	ptmx, err := pty.StartWithSize(session.command, &pty.Winsize{
		Rows: uint16(80),
		Cols: uint16(24),
	})
	if err != nil {
		return nil, err
	}
	session.ptmx = ptmx
	return session, nil
}

// Run shell session over the specified WebSocket connection. This maintains
// both directions of the connection: sending shell output to the WS, and
// receiving shell input from it. Blocks until the shell process is terminated,
// or the remote disconnects.
func (s *ShellSession) Run(connection *serverws.ShellConnection) error {
	var g errgroup.Group
	g.Go(func() error {
		err := s.command.Wait()
		log.Printf("Shell session %s terminated", s.uuid)
		s.Close()
		connection.Close()
		return err
	})
	g.Go(func() error {
		err := connection.Copy(s.ptmx, s.command)
		s.Close()
		connection.Close()
		return err
	})
	return g.Wait()
}

// Close the shell session. If the shell process is still running, it is
// forcibly killed.
func (s *ShellSession) Close() error {
	if s.command.ProcessState == nil {
		s.command.Process.Kill()
	}
	return s.ptmx.Close()
}

// Returns the UUID of the shell session.
func (s *ShellSession) Uuid() string {
	return s.uuid
}
