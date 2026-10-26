package actions

import (
	"context"
	b64 "encoding/base64"
	"io/fs"
	"os"
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
	Execute(context.Context, string) ActionResult
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

func (a CommandAction) Execute(cancelCtx context.Context, execId string) ActionResult {
	ctx := context.Background()
	if a.Timeout > 0 {
		var cancel context.CancelFunc
		duration := time.Duration(a.Timeout*1e6) * time.Microsecond
		ctx, cancel = context.WithTimeout(cancelCtx, duration)
		defer cancel()
	}
	cmd := exec.CommandContext(ctx, a.Command[0], a.Command[1:]...)
	cmd.WaitDelay = time.Duration(ActionCommandWaitDelay)
	dir, err := os.MkdirTemp("", a.Id)
	if err != nil {
		log.Errorf("Failed to create temporary action directory: %s", err.Error())
		msg := err.Error()
		return ActionResult{ExecId: execId, StatusCode: 1, Stdout: &msg}
	}
	cmd.Env = append(cmd.Env, "RDFM_ACTION_OUTPUT_DIR="+dir)
	log.Debugf("Executing action command: ['%s'] in directory '%s'", strings.Join(a.Command, "', '"), dir)

	outputBytes, _ := cmd.CombinedOutput()
	output := b64.StdEncoding.EncodeToString(outputBytes)
	status_code := cmd.ProcessState.ExitCode()

	generatedFiles := []string{}
	err = fs.WalkDir(os.DirFS(dir), ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		generatedFiles = append(generatedFiles, path)
		return nil
	})

	return ActionResult{
		ExecId:           execId,
		StatusCode:       status_code,
		Stdout:           &output,
		GeneratedFileDir: dir,
		GeneratedFiles:   generatedFiles,
	}
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

func (a CallbackAction) Execute(cancelCtx context.Context, execId string) ActionResult {
	output, err := a.Callback()
	status_code := 0
	if err != nil {
		status_code = 1
	}
	output_b64 := b64.StdEncoding.EncodeToString([]byte(output))
	return ActionResult{ExecId: execId, StatusCode: status_code, Stdout: &output_b64}
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
