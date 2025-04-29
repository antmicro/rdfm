package actions

import (
	"bytes"
	"encoding/gob"
)

type ActionRequest struct {
	ExecId   string
	ActionId string
}

func (ar *ActionRequest) Serialize() ([]byte, error) {
	var buffer bytes.Buffer

	enc := gob.NewEncoder(&buffer)
	err := enc.Encode(*ar)
	if err != nil {
		return nil, err
	}

	return buffer.Bytes(), nil
}

func NewActionRequest(raw []byte) (*ActionRequest, error) {
	var ret ActionRequest

	r := bytes.NewReader(raw)
	dec := gob.NewDecoder(r)

	err := dec.Decode(&ret)
	if err != nil {
		return nil, err
	}

	return &ret, nil

}

type ActionResult struct {
	ExecId     string
	StatusCode int
	Output     *string
}

func (ar *ActionResult) Serialize() ([]byte, error) {
	var buffer bytes.Buffer

	enc := gob.NewEncoder(&buffer)
	err := enc.Encode(*ar)
	if err != nil {
		return nil, err
	}

	return buffer.Bytes(), nil
}

func NewActionResult(raw []byte) (*ActionResult, error) {
	var ret ActionResult

	r := bytes.NewReader(raw)
	dec := gob.NewDecoder(r)

	err := dec.Decode(&ret)
	if err != nil {
		return nil, err
	}

	// https://github.com/golang/go/issues/10905
	if ret.Output == nil {
		ret.Output = new(string)
	}

	return &ret, nil
}
