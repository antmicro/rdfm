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

type Client struct {
	Name         string                          `json:"name"`
	Group        ClientType                      `json:"group"`
	Capabilities capabilities.DeviceCapabilities `json:"capabilities"`
	MacAddress   string                          `json:"mac_address"`
}

func CanHandleRequest(req Request, c capabilities.DeviceCapabilities) bool {
	switch req.(type) {
	case Proxy:
		return c.ShellConnect
	case Upload:
		return c.FileTransfer
	case Download:
		return c.FileTransfer
	default:
		return true
	}
}

type CapabilityReport struct {
	Method       string                          `json:"method"`
	Capabilities capabilities.DeviceCapabilities `json:"capabilities"`
}

func (r CapabilityReport) method() string {
	return r.Method
}

type Proxy struct {
	Method string `json:"method"`
	Port   uint16 `json:"port"`
}

func (r Proxy) method() string {
	return r.Method
}

type Update struct {
	Method string `json:"method"`
}

func (r Update) method() string {
	return r.Method
}

type Metadata struct {
	Method   string   `json:"method"`
	Metadata JsonType `json:"metadata"`
}

func (r Metadata) method() string {
	return r.Method
}

type Register struct {
	Client Client `json:"client"`
	Method string `json:"method"`
}

func (r Register) method() string {
	return r.Method
}

type Download struct {
	FilePath string `json:"file_path"`
	Url      string `json:"url"`
	Method   string `json:"method"`
}

func (r Download) method() string {
	return r.Method
}

type Upload struct {
	FilePath string `json:"file_path"`
	Method   string `json:"method"`
}

func (r Upload) method() string {
	return r.Method
}

type Auth struct {
	Jwt    string `json:"jwt"`
	Method string `json:"method"`
}

func (r Auth) method() string {
	return r.Method
}

type Alert struct {
	Method string                 `json:"method"`
	Alert  map[string]interface{} `json:"alert"`
}

func (r Alert) method() string {
	return r.Method
}

func Parse(r string) (Request, error) {
	var err error
	method := gojsonq.New().FromString(r).Find("method")
	switch method {
	case "auth_token":
		var parsed Auth
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "alert":
		var parsed Alert
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "proxy":
		var parsed Proxy
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "update":
		var parsed Update
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "metadata":
		var parsed Metadata
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "register":
		var parsed Register
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "download":
		var parsed Download
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	case "upload":
		var parsed Upload
		err = json.Unmarshal([]byte(r), &parsed)
		return parsed, nil
	}

	if err != nil {
		return nil, nil
	}
	return nil, nil
}
