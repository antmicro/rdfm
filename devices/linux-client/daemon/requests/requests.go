package requests

import (
	"encoding/json"

	"github.com/antmicro/rdfm/daemon/capabilities"

	"github.com/thedevsaddam/gojsonq"
)

type Request interface {
	method() string
}

type ClientType string
type JsonType map[string]interface{}

const (
	DeviceType ClientType = "DEVICE"
)

type Alert struct {
	Method string                 `json:"method"`
	Alert  map[string]interface{} `json:"alert"`
}

func (r Alert) method() string {
	return r.Method
}

type CapabilityReport struct {
	Method       string                          `json:"method"`
	Capabilities capabilities.DeviceCapabilities `json:"capabilities"`
}

func (r CapabilityReport) method() string {
	return r.Method
}

type DeviceAttachToManager struct {
	Method  string `json:"method"`
	MacAddr string `json:"mac_addr"`
	Uuid    string `json:"uuid"`
}

func (r DeviceAttachToManager) method() string {
	return r.Method
}

type Action struct {
	ActionId    string   `json:"action_id"`
	ActionName  string   `json:"action_name"`
	Description string   `json:"description"`
	Command     []string `json:"command"`
	Timeout     float32  `json:"timeout"`
}

type ActionExec struct {
	Method      string `json:"method"`
	ExecutionId string `json:"execution_id"`
	ActionId    string `json:"action_id"`
}

func (r ActionExec) method() string {
	return r.Method
}

type ActionExecResult struct {
	Method      string `json:"method"`
	ExecutionId string `json:"execution_id"`
	StatusCode  int    `json:"status_code"`
	Output      string `json:"output"`
}

func (r ActionExecResult) method() string {
	return r.Method
}

type ActionExecControl struct {
	Method      string `json:"method"`
	ExecutionId string `json:"execution_id"`
	Status      string `json:"status"`
}

func (r ActionExecControl) method() string {
	return r.Method
}

type ActionListQuery struct {
	Method string `json:"method"`
}

func (r ActionListQuery) method() string {
	return r.Method
}

type ActionListUpdate struct {
	Method  string   `json:"method"`
	Actions []Action `json:"actions"`
}

func (r ActionListUpdate) method() string {
	return r.Method
}

func CantHandleRequest() Request {
	res := Alert{
		Method: "alert",
		Alert: map[string]interface{}{
			"error": "Device cannot handle request",
		},
	}
	return res
}

func Parse(r string) (Request, error) {
	var err error
	method := gojsonq.New().FromString(r).Find("method")
	switch method {
	case "alert":
		var parsed Alert
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, err
	case "shell_attach":
		// TODO: reverse shell support
	case "action_exec":
		var parsed ActionExec
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, err
	case "action_list_query":
		var parsed ActionListQuery
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, err
	}
	if err != nil {
		return nil, nil
	}
	return nil, nil
}
