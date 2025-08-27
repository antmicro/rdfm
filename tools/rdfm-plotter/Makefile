SRC_DIR ?= ../../devices/linux-client/protos
DST_DIR ?= ./src/rdfm_plotter

generate:
	protoc --proto_path=$(SRC_DIR) --python_out=$(DST_DIR) $(SRC_DIR)/log.proto

.PHONY: generate
