package shell

import (
	"strconv"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

const (
	TestSessionUuid = "ABCDEF"
)

func TestShellRunnerBasic(t *testing.T) {
	sr, err := NewShellRunner(1)
	assert.NoError(t, err)

	_, err = sr.Spawn(TestSessionUuid, "")
	assert.NoError(t, err)
}

func TestShellRunnerLimits(t *testing.T) {
	const (
		LimitToTest = 4
	)

	sr, err := NewShellRunner(LimitToTest)
	assert.NoError(t, err)

	for i := 0; i < LimitToTest; i += 1 {
		_, err = sr.Spawn(strconv.Itoa(i), "")
		assert.NoError(t, err)
	}

	_, err = sr.Spawn(uuid.NewString(), "")
	if assert.Error(t, err) {
		assert.Equal(t, ErrSessionLimitReached, err)
	}
}

func TestShellRunnerLimitsIncrementedAfterTermination(t *testing.T) {
	sr, err := NewShellRunner(1)
	assert.NoError(t, err)

	id1 := uuid.NewString()
	id2 := uuid.NewString()

	_, err = sr.Spawn(id1, "")
	assert.NoError(t, err)

	_, err = sr.Spawn(id2, "")
	if assert.Error(t, err) {
		assert.Equal(t, ErrSessionLimitReached, err)
	}

	err = sr.Terminate(id1)
	assert.NoError(t, err)

	_, err = sr.Spawn(id2, "")
	assert.NoError(t, err)
}
