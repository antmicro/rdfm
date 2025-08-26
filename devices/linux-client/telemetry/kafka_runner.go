package telemetry

import (
	"github.com/twmb/franz-go/pkg/kerr"
	"github.com/twmb/franz-go/pkg/kgo"
	"github.com/twmb/franz-go/pkg/sasl/plain"

	"context"
	"crypto/tls"
	"errors"
	log "github.com/sirupsen/logrus"
	"strings"
	"sync"
	"time"
)

const (
	KAFKA_DEFAULT_TOPIC   = "RDFM"
	KAFKA_CLIENT_LINGER   = 5
	KAFKA_CONTEXT_TIMEOUT = 10
	KAFKA_RECORD_RETRIES  = 2
	TELEMETRY_RING_SIZE   = 50
)

func assembleRecord(msg Message, mac string) (*kgo.Record, error) {
	value, err := msg.Value(mac)
	if err != nil {
		return nil, err
	}

	r := &kgo.Record{
		Key:       msg.Key(),
		Value:     value,
		Timestamp: msg.Time(),
	}

	topic := msg.Topic()
	if topic != "" {
		r.Topic = topic
	}

	return r, nil
}

type KafkaRunner struct {
	macAddr string
	tlsConf *tls.Config

	kclient *kgo.Client

	ringBuffer *RingBuffer[*kgo.Record]
	rInCh      chan *kgo.Record
	rOutCh     chan *kgo.Record

	brokers  string
	maxBatch int32

	tokenCb func() (string, error)
}

func NewKafkaRunner(macAddr string, tlsConf *tls.Config, brokers string, maxBatch int32, tokenCb func() (string, error)) *KafkaRunner {
	rInCh := make(chan *kgo.Record)
	rOutCh := make(chan *kgo.Record, TELEMETRY_RING_SIZE)
	ringBuffer := NewRingBuffer[*kgo.Record](rInCh, rOutCh)
	go ringBuffer.Run()

	return &KafkaRunner{
		macAddr:    macAddr,
		tlsConf:    tlsConf,
		brokers:    brokers,
		maxBatch:   maxBatch,
		tokenCb:    tokenCb,
		ringBuffer: ringBuffer,
		rInCh:      rInCh,
		rOutCh:     rOutCh,
	}
}

func (kr *KafkaRunner) createClient() error {
	tlsDialer := &tls.Dialer{Config: kr.tlsConf}

	token, err := kr.tokenCb()
	if err != nil {
		return err
	}

	opts := []kgo.Opt{
		kgo.DefaultProduceTopic(KAFKA_DEFAULT_TOPIC),
		kgo.AllowAutoTopicCreation(),
		kgo.SeedBrokers(strings.Split(kr.brokers, ",")...),
		kgo.ProducerBatchMaxBytes(kr.maxBatch),
		kgo.RecordRetries(KAFKA_RECORD_RETRIES),
		kgo.DisableIdempotentWrite(),
		kgo.RequiredAcks(kgo.LeaderAck()),
		kgo.ProducerLinger(time.Duration(KAFKA_CLIENT_LINGER) * time.Second),
		kgo.ProducerBatchCompression(kgo.GzipCompression()),
		kgo.SASL(plain.Auth{
			User: kr.macAddr,
			Pass: token,
		}.AsMechanism()),
		kgo.Dialer(tlsDialer.DialContext),
	}

	kr.kclient, err = kgo.NewClient(opts...)
	return err
}

func shouldRestartClient(err error) bool {
	switch v := errors.Unwrap(err).(type) {
	case *kerr.Error:
		if kerr.SaslAuthenticationFailed == v {
			return true
		} else {
			return false
		}
	default:
		return false
	}
}

func (kr *KafkaRunner) ClientLoop(
	cancelCtx context.Context,
	msgOutCh <-chan Message) error {

	log.Debug("KafkaRunner: ClientLoop started")
	err := kr.createClient()
	if err != nil {
		return err
	}

	exitGraceful := make(chan bool)
	exitError := make(chan error)
	done := make(chan struct{})
	wg := sync.WaitGroup{}

	collect := func() {
		for {
			select {
			case <-done:
				return
			case <-exitGraceful:
			case <-exitError:
			}
		}
	}

	cleanup := func() {
		go collect()
		wg.Wait()
		close(done)
		kr.kclient.Close()
	}

	promise := func(r *kgo.Record, err error) {
		defer wg.Done()
		if err == nil {
			return
		}

		kr.rInCh <- r

		if shouldRestartClient(err) {
			exitGraceful <- true
		} else {
			exitError <- err
		}
	}

	produceAddWg := func(r *kgo.Record) {
		wg.Add(1)
		ctx, cancel := context.WithTimeout(
			cancelCtx,
			time.Duration(KAFKA_CONTEXT_TIMEOUT)*time.Second)

		kr.kclient.Produce(
			ctx,
			r,
			func(r *kgo.Record, err error) {
				promise(r, err)
				cancel()
			})
	}

	for {
		select {
		case <-cancelCtx.Done():
			cleanup()
			return nil

		case msg := <-msgOutCh:
			r, err := assembleRecord(msg, kr.macAddr)
			if err != nil {
				log.Debug("KafkaRunner: ClientLoop: failed to assemble record", err)
			} else {
				kr.rInCh <- r
			}

		case r := <-kr.rOutCh:
			produceAddWg(r)

		case <-exitGraceful:
			cleanup()
			return nil

		case err = <-exitError:
			cleanup()
			return err
		}
	}
}
