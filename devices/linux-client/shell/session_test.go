package shell

import (
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

func TestSessionSpawn(t *testing.T) {
	_, err := NewShellSession(uuid.NewString())
	assert.NoError(t, err)
}

func TestSessionClose(t *testing.T) {
	session, _ := NewShellSession(uuid.NewString())
	err := session.Close()
	assert.NoError(t, err)
}

func TestSessionCannotFindShell(t *testing.T) {
	DefaultShellList = []string{}
	_, err := NewShellSession(uuid.NewString())
	assert.ErrorIs(t, err, ErrNoShellAvailable)

	DefaultShellList = []string{
		"/this/path/will/not/exist",
	}
	_, err = NewShellSession(uuid.NewString())
	assert.ErrorIs(t, err, ErrNoShellAvailable)
}
