package telemetry

// Channel-based ring buffer based on
// https://github.com/lotusirous/go-concurrency-patterns/blob/main/17-ring-buffer-channel/main.go
// which bases on https://github.com/cloudfoundry/loggregator on Apache-2.0 license
type RingBuffer[T any] struct {
	inCh  chan T
	outCh chan T
}

func NewRingBuffer[T any](inCh chan T, outCh chan T) *RingBuffer[T] {
	return &RingBuffer[T]{
		inCh:  inCh,
		outCh: outCh,
	}
}

func (rb *RingBuffer[T]) Run() {
	for v := range rb.inCh {
		select {
		case rb.outCh <- v:
		default:
			<-rb.outCh // pop one item from outchan
			rb.outCh <- v
		}
	}
}
