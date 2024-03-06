package transport

import (
	"errors"
	"fmt"
	"rdfm-mcumgr-client/appcfg"
	"sync"
	"time"

	"mynewt.apache.org/newtmgr/newtmgr/bll"
	"mynewt.apache.org/newtmgr/newtmgr/config"
	"mynewt.apache.org/newtmgr/nmxact/sesn"
)

var tpLocks sync.Map

type bleSession struct {
	Session

	xport *bll.BllXport
}

type BLETransport struct {
	Config   appcfg.BLEConfig
	BlConfig *config.BllConfig
	Lock     *sync.Mutex

	id string
}

func InitBLETransport(cfg appcfg.BLEConfig) (*BLETransport, error) {
	id := fmt.Sprintf("%s-idx%d", cfg.PeerName, cfg.DeviceIdx)

	lock, _ := tpLocks.LoadOrStore(cfg.DeviceIdx, &sync.Mutex{})

	bc := config.NewBllConfig()
	bc.CtlrName = "default"
	bc.PeerName = cfg.PeerName
	bc.HciIdx = cfg.DeviceIdx
	bc.ConnTimeout = float64(10)

	return &BLETransport{
		Config:   cfg,
		BlConfig: bc,
		Lock:     lock.(*sync.Mutex),
		id:       id,
	}, nil
}

func (bt *BLETransport) Id() string {
	return bt.id
}

func (bt *BLETransport) AcqSession() (Session, error) {
	bt.Lock.Lock()

	xc := bll.NewXportCfg()
	xc.CtlrName = bt.BlConfig.CtlrName
	xc.OwnAddrType = bt.BlConfig.OwnAddrType

	xport := bll.NewBllXport(xc, bt.BlConfig.HciIdx)

	if err := xport.Start(); err != nil {
		bt.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed initializing BLE transport %s (err: %s)", bt.id, err))
	}

	cfg, err := config.BuildBllSesnCfg(bt.BlConfig)
	if err != nil {
		xport.Stop()
		bt.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed to configure Bluetooth session %s (err: %s)", bt.Id(), err))
	}
	cfg.MgmtProto = sesn.MGMT_PROTO_NMP
	cfg.PreferredMtu = 64

	session, err := xport.BuildBllSesn(cfg)
	if err != nil {
		xport.Stop()
		bt.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed building Bluetooth session %s (err: %s)", bt.Id(), err))
	}

	if err := session.Open(); err != nil {
		xport.Stop()
		bt.Lock.Unlock()
		return nil, errors.New(fmt.Sprintf("Failed to open Bluetooth connection %s (err: %s)", bt.Id(), err))
	}

	return &bleSession{
		Session: NewSession(session, bt.Lock),
		xport:   xport,
	}, nil
}

func (bt *BLETransport) Stop() error {
	return nil
}

func (bs *bleSession) ResetDevice() error {
	if err := bs.Session.ResetDevice(); err != nil {
		return err
	}

	time.Sleep(time.Second)
	return nil
}

func (bs *bleSession) Close() error {
	session := bs.Session.(*simpleSession)
	defer session.lock.Unlock()

	if session.s.IsOpen() {
		session.s.Close()
	}

	if err := bs.xport.Stop(); err != nil {
		return err
	}

	time.Sleep(5 * time.Second)

	return nil
}
