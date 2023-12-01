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
		return parsed, nil
	case "shell_attach":
		// TODO: reverse shell support
	}
	if err != nil {
		return nil, nil
	}
	return nil, nil
}
