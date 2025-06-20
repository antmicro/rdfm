package conf

import (
	"fmt"
	"regexp"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNetworkMatchingRegex(t *testing.T) {
	mustMatchDefaultRegex := []string{
		"eno1",
		"enp0s29",
		"enp0s31f6",
		"enp2s0f0",
		"enp2s0f1",
		"enp5s0",
		"enP8p1s0",
		"ens1",
		"ens9f0",
		"eth0",
		"eth1",
	}
	mustNotMatchDefaultRegex := []string{
		"lo",
		"docker0",
	}

	re := regexp.MustCompile(DEFAULT_MAC_ADDRESS_IF_REGEXP)
	for _, name := range mustMatchDefaultRegex {
		errString := fmt.Sprintf("Regular expression: %v must match name: %v", DEFAULT_MAC_ADDRESS_IF_REGEXP, name)
		assert.True(t, re.MatchString(name), errString)
	}
	for _, name := range mustNotMatchDefaultRegex {
		errString := fmt.Sprintf("Regular expression: %v must NOT match name: %v", DEFAULT_MAC_ADDRESS_IF_REGEXP, name)
		assert.False(t, re.MatchString(name), errString)
	}
}
