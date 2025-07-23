package protos

import (
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"
	"time"
)

func CreateLog(mac string, time time.Time, entry string) ([]byte, error) {
	log := Log{
		DeviceMac:  mac,
		DeviceTime: timestamppb.New(time),
		Entry:      entry,
	}

	buf, err := proto.Marshal(&log)
	if err != nil {
		return nil, err
	}

	return buf, nil
}

//go:generate protoc --go_out=.. -I=../protos ../protos/log.proto
