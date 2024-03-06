package transport

import (
	"errors"
	"fmt"
	"rdfm-mcumgr-client/appcfg"
	"sync"

	"mynewt.apache.org/newtmgr/nmxact/sesn"
	"mynewt.apache.org/newtmgr/nmxact/udp"
)

type UDPTransport struct {
	Config appcfg.UDPConfig
	Xport  *udp.UdpXport
	Lock   sync.Mutex
}

func InitUDPTransport(cfg appcfg.UDPConfig) (*UDPTransport, error) {
	xport := udp.NewUdpXport()

	if err := xport.Start(); err != nil {
		return nil, errors.New(fmt.Sprintf("Failed initializing UDP transport %s (err: %s)", cfg.Address, err))
	}

	return &UDPTransport{
		Config: cfg,
		Xport:  xport,
		Lock:   sync.Mutex{},
	}, nil
}

func (ut *UDPTransport) Id() string {
	return ut.Config.Address
}

func (ut *UDPTransport) AcqSession() (Session, error) {
	ut.Lock.Lock()

	cfg := sesn.NewSesnCfg()
	cfg.MgmtProto = sesn.MGMT_PROTO_NMP
	cfg.PeerSpec.Udp = ut.Config.Address

	session, err := ut.Xport.BuildSesn(cfg)
	if err != nil {
		ut.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed building UDP session %s (err: %s)", ut.Id(), err))
	}

	if err := session.Open(); err != nil {
		ut.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed to open UDP connection %s (err: %s)", ut.Id(), err))
	}

	return NewSession(session, &ut.Lock), nil
}

func (ut *UDPTransport) Stop() error {
	ut.Lock.Lock()
	defer ut.Lock.Unlock()
	return ut.Xport.Stop()
}
