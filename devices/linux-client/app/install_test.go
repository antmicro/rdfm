package app

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/sirupsen/logrus"
	"github.com/sirupsen/logrus/hooks/test"
	"github.com/stretchr/testify/assert"
)

func TestCommitScriptSuccess(t *testing.T) {
	filePath := filepath.Join(os.TempDir(), "valid-script.sh")
	file, _ := os.Create(filePath)

	content := []byte("#!/bin/bash \n echo valid \n exit 0")
	os.WriteFile(filePath, content, 0755)
	os.Chmod(filePath, 0755)
	file.Close()

	hook := test.NewGlobal()

	err := checkBeforeCommit(filePath)

	assert.NoError(t, err)
	assert.Equal(t, 2, len(hook.Entries))
	assert.Equal(t, "System correctness successfully verified", hook.Entries[0].Message)
	assert.Equal(t, "valid\n", hook.Entries[1].Message)
	assert.Equal(t, logrus.InfoLevel, hook.Entries[0].Level)
	assert.Equal(t, logrus.InfoLevel, hook.Entries[1].Level)

	os.Remove(filePath)
}

func TestCommitScriptFailure(t *testing.T) {
	filePath := filepath.Join(os.TempDir(), "invalid-script.sh")
	file, _ := os.Create(filePath)

	content := []byte("#!/bin/bash \n echo invalid \n >&2 echo error \n exit 1")
	os.WriteFile(filePath, content, 0755)
	os.Chmod(filePath, 0755)
	file.Close()

	hook := test.NewGlobal()

	err := checkBeforeCommit(filePath)

	assert.Error(t, err)
	assert.Equal(t, 2, len(hook.Entries))
	assert.Equal(t, "System correctness verification failed", hook.Entries[0].Message)
	assert.Equal(t, "invalid\nerror\n", hook.Entries[1].Message)
	assert.Equal(t, logrus.ErrorLevel, hook.Entries[0].Level)
	assert.Equal(t, logrus.ErrorLevel, hook.Entries[1].Level)

	os.Remove(filePath)
}

func TestCommitScriptNotSet(t *testing.T) {
	err := checkBeforeCommit("")
	assert.NoError(t, err)
}

func TestCommitScriptNotFound(t *testing.T) {
	err := checkBeforeCommit("/this/path/is/invalid")
	assert.ErrorIs(t, err, os.ErrNotExist)
}
