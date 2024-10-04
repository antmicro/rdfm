package helpers

import (
	"time"
)

func NowAsServerTime() string {
	return time.Now().UTC().Format(time.RFC1123Z)
}

func TimeToServerTime(t time.Time) string {
	return t.UTC().Format(time.RFC1123Z)
}
