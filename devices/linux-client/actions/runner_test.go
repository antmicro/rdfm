package actions

import (
	"context"
	"os"
	"path"
	"testing"
	"time"

	"github.com/antmicro/rdfm/app"
	"github.com/antmicro/rdfm/conf"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

const (
	TestActionTimeout = 5 * time.Second
)

func createTestRdfmContext() *app.RDFM {
	testContext := new(app.RDFM)
	testContext.RdfmConfig = new(conf.RDFMConfig)
	testContext.RdfmActionsConfig = new([]conf.RDFMActionsConfiguration)
	testContext.RdfmTelemetryConfig = new(map[string]conf.RDFMLoggerConfiguration)
	return testContext
}

func prepareRunner(queueSize int, callback ActionResultCallback, datadir string, actions []conf.RDFMActionsConfiguration) (*ActionRunner, context.CancelFunc) {
	rdfmContext := createTestRdfmContext()
	rdfmContext.RdfmActionsConfig = &actions
	context, cancel := context.WithCancel(context.Background())
	runner, _ := NewActionRunner(rdfmContext, queueSize, callback, datadir)
	go runner.StartWorker(context)
	return runner, cancel
}

func TestActionRunnerSimpleSetup(t *testing.T) {
	ctx := createTestRdfmContext()
	_, err := NewActionRunner(ctx, 32, func(ActionResult, context.Context) bool {
		return true
	}, t.TempDir())
	assert.Nil(t, err)
}

func TestActionRunnerExecuteSimple(t *testing.T) {
	testFilePath := path.Join(t.TempDir(), ".test-action-file")
	actions := []conf.RDFMActionsConfiguration{
		{
			Id:          "test_action",
			Name:        "",
			Description: "",
			Command: []string{
				"touch", testFilePath,
			},
			Timeout: float32(TestActionTimeout),
		},
	}
	callback := func(ActionResult, context.Context) bool {
		return true
	}
	runner, _ := prepareRunner(32, callback, t.TempDir(), actions)

	ok := runner.Execute(uuid.NewString(), "test_action")
	assert.True(t, ok)
	time.Sleep(TestActionTimeout)
	// The file should exist if the action was executed successfully.
	_, err := os.Stat(testFilePath)
	assert.Nil(t, err)
	assert.NotErrorIs(t, err, os.ErrNotExist)
}

func TestActionRunnerResultCallback(t *testing.T) {
	actions := []conf.RDFMActionsConfiguration{
		{
			Id:          "test_action",
			Name:        "",
			Description: "",
			Command: []string{
				"uname",
			},
			Timeout: float32(TestActionTimeout),
		},
	}
	ch := make(chan ActionResult)
	callback := func(result ActionResult, ctx context.Context) bool {
		ch <- result
		return true
	}

	actionId := uuid.NewString()
	runner, _ := prepareRunner(32, callback, t.TempDir(), actions)
	ok := runner.Execute(actionId, "test_action")
	assert.True(t, ok)
	timeoutCtx, _ := context.WithTimeout(context.Background(), TestActionTimeout)

	select {
	case result := <-ch:
		{
			assert.Equal(t, result.ExecId, actionId)
			assert.Equal(t, result.StatusCode, 0)
			assert.NotEmpty(t, result.Output)
		}
	case <-timeoutCtx.Done():
		{
			assert.Fail(t, "Timeout when waiting for action result")
		}
	}
}

func TestActionRunnerConcurrentActionLimit(t *testing.T) {
	actions := []conf.RDFMActionsConfiguration{
		{
			Id:          "test_action",
			Name:        "",
			Description: "",
			Command: []string{
				"cat",
			},
			Timeout: float32(TestActionTimeout),
		},
	}
	callback := func(ActionResult, context.Context) bool {
		return true
	}
	queueSize := 2
	runner, cancel := prepareRunner(queueSize, callback, t.TempDir(), actions)
	defer cancel()

	for i := 0; i < queueSize; i++ {
		ok := runner.Execute(uuid.NewString(), "test_action")
		assert.True(t, ok)
	}
	// This should fail as the queue size was reached.
	ok := runner.Execute(uuid.NewString(), "test_action")
	assert.False(t, ok)
}
