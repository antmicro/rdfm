package actions

import (
	"context"
	"os/exec"
	"strings"
	"time"

	"github.com/antmicro/rdfm/devices/linux-client/conf"
	log "github.com/sirupsen/logrus"
)

const (
	// Additional time to wait for fds of the action command to be closed. This
	// prevents the action runner from getting stuck waiting for a child that
	// has already terminated, but did not close its file descriptors.
	ActionCommandWaitDelay = time.Duration(time.Second * 5)
)

type Action interface {
	Execute(context.Context) (int, []byte)
	GetId() string
	GetName() string
	GetDescription() string
}

type CommandAction struct {
	Id          string
	Name        string
	Description string
	Command     []string
	Timeout     float32
}

type ActionCallback func() (string, error)

type CallbackAction struct {
	Id          string
	Name        string
	Description string
	Callback    ActionCallback
}

func (a CommandAction) Execute(cancelCtx context.Context) (int, []byte) {
	ctx := context.Background()
	if a.Timeout > 0 {
		var cancel context.CancelFunc
		duration := time.Duration(a.Timeout*1e6) * time.Microsecond
		ctx, cancel = context.WithTimeout(cancelCtx, duration)
		defer cancel()
	}
	log.Debugf("Executing action command: ['%s']", strings.Join(a.Command, "', '"))
	cmd := exec.CommandContext(ctx, a.Command[0], a.Command[1:]...)
	cmd.WaitDelay = time.Duration(ActionCommandWaitDelay)

	output, _ := cmd.CombinedOutput()
	status_code := cmd.ProcessState.ExitCode()

	return status_code, output
}

func (a CommandAction) GetId() string {
	return a.Id
}

func (a CommandAction) GetName() string {
	return a.Name
}

func (a CommandAction) GetDescription() string {
	return a.Description
}

func (a CallbackAction) Execute(cancelCtx context.Context) (int, []byte) {
	output, err := a.Callback()
	status_code := 0
	if err != nil {
		status_code = 1
	}
	return status_code, []byte(output)
}

func (a CallbackAction) GetId() string {
	return a.Id
}

func (a CallbackAction) GetName() string {
	return a.Name
}

func (a CallbackAction) GetDescription() string {
	return a.Description
}

func NewCommandAction(cfg conf.RDFMCommandActionConfiguration) Action {
	return CommandAction{
		Id:          cfg.Id,
		Name:        cfg.Name,
		Description: cfg.Description,
		Command:     cfg.Command,
		Timeout:     cfg.Timeout,
	}
}

func NewBuiltInAction(id string, name string, description string, callback ActionCallback) Action {
	return CallbackAction{
		Id:          id,
		Name:        name,
		Description: description,
		Callback:    callback,
	}
}
