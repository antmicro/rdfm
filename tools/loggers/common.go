package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

// Represents a set of named tags.
type Tags map[string]string

// Adds a new named tag or appends an existing one.
func (tags Tags) Concat(key, value string) {
	if _, ok := tags[key]; !ok {
		tags[key] = ""
	} else {
		tags[key] += "; "
	}
	tags[key] += value
}

// Returns a union of two sets of tags, common tags get concatenated.
func (tags Tags) Join(from Tags) {
	for key, value := range from {
		tags.Concat(key, value)
	}
}

// Returns a CSV representation for a set of tags.
func (tags Tags) CSV() string {
	bytes, _ := json.Marshal(tags)
	csv := string(bytes)
	csv = strings.ReplaceAll(csv, `"`, `""`)
	return fmt.Sprint(`"`, csv, `"`)
}
