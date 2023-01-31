package helpers

import (
	"bufio"
	"errors"
	"os"
	"strings"
)

// Loads all "key=value" pairs from the specified file
// - All leading and trailing whitespace is removed.
// - Duplicate keys are not allowed.
// - Empty values are not allowed.
func LoadKeyValueFile(path string) (map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	pairs := make(map[string]string)

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			return nil, errors.New("malformed key/value entry: '" + line + "'")
		}

		key, val := strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
		if key == "" {
			return nil, errors.New("empty key found")
		}
		if val == "" {
			return nil, errors.New("empty value for key '" + key + "'")
		}
		if pairs[key] != "" {
			return nil, errors.New("duplicate key '" + key + "'")
		}
		pairs[key] = val
	}

	return pairs, nil
}
