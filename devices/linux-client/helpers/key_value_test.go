package helpers

import (
	"fmt"
	"os"
	"reflect"
	"testing"
)

func makeTempOrFatal(t *testing.T) *os.File {
	f, err := os.CreateTemp(os.TempDir(), "rdfmKeyValueTest")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}

	return f
}

func makeTempWithContents(t *testing.T, contents string) *os.File {
	f := makeTempOrFatal(t)
	f.WriteString(contents)
	err := f.Sync()
	if err != nil {
		t.Fatalf("Failed flushing temporary file: %v", err)
	}

	return f
}

func doKeyValueLoad(t *testing.T, input string) (map[string]string, error) {
	f := makeTempWithContents(t, input)
	defer func() {
		name := f.Name()
		f.Close()
		os.Remove(name)
	}()

	return LoadKeyValueFile(f.Name())
}

func testExpectedOutput(t *testing.T, input string, expectedOutput map[string]string) {
	pairs, err := doKeyValueLoad(t, input)
	if err != nil {
		t.Errorf("expected output for input: %q, got error instead: %q", input, err)
	}

	if !reflect.DeepEqual(pairs, expectedOutput) {
		t.Errorf("output: %q does not match the expected output: %q", pairs, expectedOutput)
	}
}

func testExpectedError(t *testing.T, input string) {
	pairs, err := doKeyValueLoad(t, input)
	if err == nil {
		t.Errorf("expected error for input: %q, got value instead: %q", input, pairs)
	}
}

type testCase struct {
	input  string
	output map[string]string
}

func newTestCase(input string, output map[string]string) testCase {
	return testCase{
		input: input, output: output,
	}
}

func TestLoadKeyPairs(t *testing.T) {
	outputTestCases := []testCase{
		newTestCase(
			"foo=bar\nbaz=quux",
			map[string]string{
				"foo": "bar",
				"baz": "quux",
			},
		),
		newTestCase(
			"    foo=bar    \n    baz=quux    ",
			map[string]string{
				"foo": "bar",
				"baz": "quux",
			},
		),
	}
	errorTestCases := []string{
		"foo=",             // empty value
		"=bar",             // empty key
		"=",                // malformed
		"foo=bar\nfoo=baz", // duplicate key
	}

	for idx, v := range outputTestCases {
		t.Run(fmt.Sprintf("Expected Output #%d", idx), func(t *testing.T) {
			testExpectedOutput(t, v.input, v.output)
		})
	}

	for idx, v := range errorTestCases {
		t.Run(fmt.Sprintf("Expected Error #%d", idx), func(t *testing.T) {
			testExpectedError(t, v)
		})
	}

}
