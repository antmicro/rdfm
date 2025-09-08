package actions

import (
	"context"
	b64 "encoding/base64"
	"path"
	"sync"
	"time"

	"github.com/antmicro/rdfm/devices/linux-client/app"

	log "github.com/sirupsen/logrus"
)

type ActionResultCallback func(ActionResult, context.Context) bool

type ActionRunner struct {
	rdfmCtx   *app.RDFM
	reqStore  *FileStore
	resStore  *FileStore
	actionMap map[string]Action
	resultCb  ActionResultCallback
}

func (r *ActionRunner) runCommand(req ActionRequest, cancelCtx context.Context) ActionResult {
	action := r.actionMap[req.ActionId]
	log.Infof("Running action %s with execution id %s", action.GetName(), req.ExecId)

	status_code, outputBytes := action.Execute(cancelCtx)

	output := b64.StdEncoding.EncodeToString(outputBytes)

	log.Infoln("Action finished with status code:", status_code)

	return ActionResult{req.ExecId, status_code, &output}
}

func (r *ActionRunner) startCommandLoop(cancelCtx context.Context) error {
	for {
		select {
		case <-cancelCtx.Done():
			return nil
		default:
		}
		bytes, err := r.reqStore.Dequeue(cancelCtx)
		if err != nil {
			log.Warnln("Failed to dequeue action:", err)
			continue
		}
		cmd, err := NewActionRequest(bytes)
		if err != nil {
			log.Warnln("Failed to deserialize action:", err)
			continue
		}
		ret := r.runCommand(*cmd, cancelCtx)
		result, err := ret.Serialize()
		if err != nil {
			log.Warnln("Failed to serialize result:", err)
			continue
		}
		err = r.resStore.Enqueue(result, cancelCtx)
		if err != nil {
			log.Warnln("Failed to enqueue result:", err)
			continue
		}
	}
}

func (r *ActionRunner) startResponderLoop(cancelCtx context.Context) error {
	for {
		select {
		case <-cancelCtx.Done():
			return nil
		default:
		}
		err := r.resStore.WaitNonEmpty(cancelCtx)
		if err != nil {
			log.Warnln("Failed to wait for new result:", err)
			continue
		}
		bytes := r.resStore.Peek()
		if bytes == nil {
			log.Warnln("Queue did not contain result, but we were woken up")
			continue
		}
		result, err := NewActionResult(bytes)
		if err != nil {
			log.Warnln("Failed to deserialize result:", err)
			continue
		}
		// NOTE: The error retry mechanism here is minimal on purpose and only
		// aims to prevent us from busy-spinning when resultCb does not
		// implement any retry mechanism on its own.
		for {
			ok := r.resultCb(*result, cancelCtx)
			if ok {
				break
			}
			time.Sleep(1 * time.Second)
		}
		err = r.resStore.Pop()
		if err != nil {
			log.Warnln("Failed to pop response:", err)
		}
	}
}

func (r *ActionRunner) StartWorker(cancelCtx context.Context) {
	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Infoln("Starting command loop...")
		err := r.startCommandLoop(cancelCtx)
		if err != nil {
			log.Warnln("Command loop exited due to an error:", err)
		} else {
			log.Infoln("Command loop exited.")
		}
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Infoln("Starting action result sender...")
		err := r.startResponderLoop(cancelCtx)
		if err != nil {
			log.Warnln("Result sender exited due to an error:", err)
		} else {
			log.Infoln("Result sender exited.")
		}
	}()

	wg.Wait()
}

func (r *ActionRunner) Execute(executionId string, actionId string) bool {
	req := ActionRequest{executionId, actionId}

	reqBytes, err := req.Serialize()
	if err != nil {
		return false
	}

	err = r.reqStore.TryEnqueue(reqBytes)
	if err != nil {
		return false
	}
	return true
}

func (r *ActionRunner) List() []Action {
	var actions []Action
	for _, v := range r.actionMap {
		actions = append(actions, v)
	}
	return actions
}

func NewActionRunner(rdfmCtx *app.RDFM, queueSize int, resultCb ActionResultCallback, dataDirectory string) (*ActionRunner, error) {
	r := new(ActionRunner)
	r.rdfmCtx = rdfmCtx
	r.resultCb = resultCb
	r.RebuildActionMap()

	reqStore, err := NewFileStore(path.Join(dataDirectory, "req"), queueSize)
	if err != nil {
		return nil, err
	}
	r.reqStore = reqStore

	resStore, err := NewFileStore(path.Join(dataDirectory, "res"), queueSize)
	if err != nil {
		return nil, err
	}
	r.resStore = resStore

	return r, nil
}

func (r *ActionRunner) RebuildActionMap() {
	r.actionMap = make(map[string]Action)
	for _, action := range *r.rdfmCtx.RdfmActionsConfig {
		r.actionMap[action.Id] = NewCommandAction(action)
	}
}

func (r *ActionRunner) RegisterAction(action Action) {
	r.actionMap[action.GetId()] = action
}
