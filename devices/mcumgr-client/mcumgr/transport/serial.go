package transport

import (
	"errors"
	"fmt"
	"rdfm-mcumgr-client/appcfg"
	"sync"
	"time"

	"mynewt.apache.org/newtmgr/nmxact/nmserial"
	"mynewt.apache.org/newtmgr/nmxact/sesn"
)

type SerialTransport struct {
	Config appcfg.SerialConfig
	Xport  *nmserial.SerialXport
	Lock   sync.Mutex
}

func InitSerialTransport(cfg appcfg.SerialConfig) (*SerialTransport, error) {
	sc := nmserial.NewXportCfg()
	sc.DevPath = cfg.Device
	sc.Baud = cfg.Baud
	sc.Mtu = cfg.Mtu
	sc.ReadTimeout = 10 * time.Second

	xport := nmserial.NewSerialXport(sc)

	if err := xport.Start(); err != nil {
		return nil, errors.New(fmt.Sprintf("Failed initializing serial transport %s (err: %s)", cfg.Device, err))
	}

	return &SerialTransport{
		Config: cfg,
		Xport:  xport,
		Lock:   sync.Mutex{},
	}, nil
}

func (st *SerialTransport) Id() string {
	return st.Config.Device
}

func (st *SerialTransport) AcqSession() (Session, error) {
	st.Lock.Lock()

	cfg := sesn.NewSesnCfg()
	cfg.MgmtProto = sesn.MGMT_PROTO_NMP

	session, err := st.Xport.BuildSesn(cfg)
	if err != nil {
		st.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed building serial session %s (err: %s)", st.Id(), err))
	}

	if err := session.Open(); err != nil {
		st.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed to open serial connection %s (err: %s)", st.Id(), err))
	}

	return NewSession(session, &st.Lock), nil
}

func (st *SerialTransport) Stop() error {
	st.Lock.Lock()
	defer st.Lock.Unlock()

	return st.Xport.Stop()
}
