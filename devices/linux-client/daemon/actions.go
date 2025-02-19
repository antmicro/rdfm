package daemon

import (
	"context"
	b64 "encoding/base64"
	"errors"
	"os/exec"
	"sync"
	"time"

	"github.com/antmicro/rdfm/app"

	log "github.com/sirupsen/logrus"

	dconf "github.com/antmicro/rdfm/daemon/conf"
)

type actionReq struct {
	exec_id   string
	action_id string
}

type actionRes struct {
	exec_id     string
	status_code int
	output      *string
}

type ActionRunner struct {
	requests  chan actionReq
	results   chan actionRes
	rdfmCtx   *app.RDFM
	actionMap map[string]dconf.RDFMActionsConfiguration
}

func (r *ActionRunner) runCommand(req actionReq, cancelCtx context.Context) actionRes {
	action := r.actionMap[req.action_id]
	log.Infof("Running action %s with execution id %s", action.Name, req.exec_id)

	ctx := context.Background()
	if action.Timeout > 0 {
		var cancel context.CancelFunc
		duration := time.Duration(action.Timeout*1e6) * time.Microsecond
		ctx, cancel = context.WithTimeout(cancelCtx, duration)
		defer cancel()
	}
	cmd := exec.CommandContext(ctx, action.Command[0], action.Command[1:]...)

	outputBytes, _ := cmd.CombinedOutput()

	status_code := cmd.ProcessState.ExitCode()

	log.Infoln("Action finished with status code:", status_code)

	output := b64.StdEncoding.EncodeToString(outputBytes)

	res := actionRes{req.exec_id, status_code, &output}
	return res
}

func (r *ActionRunner) startCommandLoop(cancelCtx context.Context) error {
	var cmd actionReq
	var cmdOk bool
	for {
		select {
		case cmd, cmdOk = <-r.requests:
			if !cmdOk {
				return errors.New("command channel closed")
			}
		case <-cancelCtx.Done():
			return nil
		}

		result := r.runCommand(cmd, cancelCtx)

		select {
		case r.results <- result:
		case <-cancelCtx.Done():
			return nil
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
			log.Fatalln("Command loop exited due to an error:", err)
		} else {
			log.Infoln("Command loop exited.")
		}
	}()

	wg.Wait()
}

func (r *ActionRunner) Execute(executionId string, actionId string) bool {
	req := actionReq{executionId, actionId}

	if !(cap(r.results)-len(r.results) > len(r.requests)) {
		return false
	}

	select {
	case r.requests <- req:
	default:
		return false
	}
	return true
}

func (r *ActionRunner) Fetch(cancelCtx context.Context) (*string, int, *string) {
	select {
	case res := <-r.results:
		return &res.exec_id, res.status_code, res.output
	case <-cancelCtx.Done():
		return nil, 0, nil
	}

}

func (r *ActionRunner) List() []dconf.RDFMActionsConfiguration {
	return *r.rdfmCtx.RdfmActionsConfig
}

func NewActionRunner(rdfmCtx *app.RDFM, queueSize int) *ActionRunner {
	r := new(ActionRunner)
	r.requests = make(chan actionReq, queueSize)
	r.results = make(chan actionRes, queueSize)
	r.rdfmCtx = rdfmCtx
	r.RebuildActionMap()
	return r
}

func (r *ActionRunner) RebuildActionMap() {
	r.actionMap = make(map[string]dconf.RDFMActionsConfiguration)
	for _, action := range *r.rdfmCtx.RdfmActionsConfig {
		r.actionMap[action.Id] = action
	}
}
