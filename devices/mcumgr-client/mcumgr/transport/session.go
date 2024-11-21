package transport

import (
	"errors"
	"fmt"
	"strings"
	"sync"

	"mynewt.apache.org/newtmgr/nmxact/nmp"
	"mynewt.apache.org/newtmgr/nmxact/sesn"
	"mynewt.apache.org/newtmgr/nmxact/xact"
)

type Session interface {
	Ping() error
	ReadDeviceImages() ([]nmp.ImageStateEntry, error)
	WriteImage(image []byte) error
	SetPendingImage(imgHash []byte) error
	ConfirmImage(imgHash []byte) error
	ResetDevice() error

	Close() error
}

type simpleSession struct {
	s    sesn.Sesn
	lock *sync.Mutex
}

func NewSession(s sesn.Sesn, sLock *sync.Mutex) Session {
	return &simpleSession{
		s:    s,
		lock: sLock,
	}
}

func (s *simpleSession) Ping() error {
	const payload = "Pong"

	cmd := xact.NewEchoCmd()
	cmd.SetTxOptions(sesn.DfltTxOptions)
	cmd.Payload = payload

	resp, err := cmd.Run(s.s)
	if err != nil {
		return errors.New(fmt.Sprintf("Ping failed (err: %s)", err))
	}

	if p := resp.(*xact.EchoResult).Rsp.Payload; p != payload {
		return errors.New(fmt.Sprintf("Bad Pong response (expected '%s', got '%s')", payload, p))
	}

	return nil
}

func (s *simpleSession) ReadDeviceImages() ([]nmp.ImageStateEntry, error) {
	cmd := xact.NewImageStateReadCmd()

	resp, err := cmd.Run(s.s)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("Reading primary image failed (err: %s)", err))
	}

	images := resp.(*xact.ImageStateReadResult).Rsp.Images

	for i, image := range images {
		// Change Maj.Min.Patch.Rev -> Maj.Min.Patch+Rev
		if version := image.Version; strings.Count(version, ".") == 3 {
			ci := strings.LastIndex(version, ".")
			images[i].Version = fmt.Sprintf("%s+%s", version[:ci], version[ci+1:])
		}
	}

	return images, nil
}

func (s *simpleSession) WriteImage(image []byte) error {
	cmd := xact.NewImageUpgradeCmd()

	cmd.Data = image
	cmd.NoErase = false
	cmd.ImageNum = 0
	cmd.Upgrade = false
	cmd.LastOff = 0
	// NOTE: cmd.MaxWinSz being greater than xact.IMAGE_UPLOAD_START_WS
	// runs the risk of deadlocking the client during image upload.
	//
	// Before the below fix the problem occurred frequently during
	// CI runs. Devices were stopping the update and timing out randomly.
	//
	// A race condition in newtmgr caused a deadlock, specifically on this line:
	// https://github.com/apache/mynewt-newtmgr/blob/d56acd2e28855562923ce901c55997822618a420/nmxact/xact/image.go#L347
	// The channel `ch` not being read from causes the update loop to halt.
	//
	// HACK: Setting cmd.MaxWinSz to xact.IMAGE_UPLOAD_START_WS sidesteps this
	// by preventing newtmgr's `ImageUploadIntTracker.WCap` variable from
	// being incremented/decremented. Not allowing `WCap` to be modified
	// prevents the race from occurring.
	cmd.MaxWinSz = xact.IMAGE_UPLOAD_START_WS
	cmd.ProgressCb = func(c *xact.ImageUploadCmd, r *nmp.ImageUploadRsp) {}

	resp, err := cmd.Run(s.s)
	if err != nil {
		return errors.New(fmt.Sprintf("Writing image failed (err: %s)", err))
	}

	if status := resp.Status(); status != nmp.NMP_ERR_OK {
		return errors.New(fmt.Sprintf("Writing image failed (err: NMP err %d)", status))
	}

	return nil
}

func (s *simpleSession) SetPendingImage(imgHash []byte) error {
	cmd := xact.NewImageStateWriteCmd()

	cmd.Hash = imgHash
	cmd.Confirm = false

	resp, err := cmd.Run(s.s)
	if err != nil {
		return errors.New(fmt.Sprintf("Setting image as pending failed (err: %s)", err))
	}

	if status := resp.Status(); status != nmp.NMP_ERR_OK {
		return errors.New(fmt.Sprintf("Setting image as pending failed (err: NMP err %d)", status))
	}

	return nil
}

func (s *simpleSession) ConfirmImage(imgHash []byte) error {
	cmd := xact.NewImageStateWriteCmd()

	cmd.Hash = imgHash
	cmd.Confirm = true

	resp, err := cmd.Run(s.s)
	if err != nil {
		return errors.New(fmt.Sprintf("Confirming new image failed (err: %s)", err))
	}

	if status := resp.Status(); status != nmp.NMP_ERR_OK {
		return errors.New(fmt.Sprintf("Confirming new image failed (err: NMP err %d)", status))
	}

	return nil
}

func (s *simpleSession) ResetDevice() error {
	cmd := xact.NewResetCmd()

	if _, err := cmd.Run(s.s); err != nil {
		return errors.New(fmt.Sprintf("Resetting device failed (err: %s)", err))
	}

	return nil
}

func (s *simpleSession) Close() error {
	defer s.lock.Unlock()
	return s.s.Close()
}
