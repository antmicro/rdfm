GO ?= go
GOFMT ?= gofmt
V ?=
PREFIX ?= /usr/local
PKGS = $(shell go list ./... | grep -v vendor)
SUBPKGS = $(shell go list ./... | sed '1d' | tr '\n' ',' | sed 's/,$$//1')
PKGNAME = rdfm-artifact
PKGFILES = $(shell find . \( -path ./vendor -o -path ./Godeps \) -prune \
		-o -type f -name '*.go' -print)
PKGFILES_notest = $(shell echo $(PKGFILES) | tr ' ' '\n' | grep -v _test.go)
GOCYCLO ?= 20

CGO_ENABLED=1
export CGO_ENABLED

VERSION = $(shell git describe --tags --dirty --exact-match 2>/dev/null || git rev-parse --short HEAD)

GO_LDFLAGS = \
	-ldflags "-X github.com/antmicro/rdfm-artifact/cli.Version=$(VERSION)"

ifeq ($(V),1)
BUILDV = -v
endif

TAGS =
ifeq ($(LOCAL),1)
TAGS += local
endif

ifneq ($(TAGS),)
BUILDTAGS = -tags '$(TAGS)'
endif

build:
	$(GO) build $(GO_LDFLAGS) $(BUILDV) $(BUILDTAGS)

PLATFORMS := darwin linux windows

GO_LDFLAGS_WIN = -ldflags "-X github.com/antmicro/rdfm-artifact/cli.Version=$(VERSION) -linkmode=internal -s -w -extldflags '-static' -extld=x86_64-w64-mingw32-gcc"

build-natives:
	@arch="amd64";
	@echo "building mac";
	@env GOOS=darwin GOARCH=$$arch CGO_ENABLED=0 \
		$(GO) build -a $(GO_LDFLAGS) $(BUILDV) $(BUILDTAGS) -o $(PKGNAME)-darwin ;
	@echo "building linux";
	@env GOOS=linux GOARCH=$$arch \
		$(GO) build -a $(GO_LDFLAGS) $(BUILDV) $(BUILDTAGS) -o $(PKGNAME)-linux ;
	@echo "building windows";
	@env GOOS=windows GOARCH=$$arch CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++ \
		$(GO) build $(GO_LDFLAGS_WIN) $(BUILDV) -tags $(TAGS) nolzma -o $(PKGNAME)-windows.exe ;

build-contained:
	rm -f rdfm-artifact && \
	image_id=$$(docker build -f Dockerfile . | awk '/Successfully built/{print $$NF;}') && \
	docker run --rm --entrypoint "/bin/sh" -v $(shell pwd):/binary $$image_id -c "cp /go/bin/rdfm-artifact /binary" && \
	docker image rm $$image_id

build-natives-contained:
	rm -f rdfm-artifact && \
	image_id=$$(docker build -f Dockerfile.binaries . | awk '/Successfully built/{print $$NF;}') && \
	docker run --rm --entrypoint "/bin/sh" -v $(shell pwd):/binary $$image_id -c "cp /go/bin/rdfm-artifact* /binary" && \
	docker image rm $$image_id

install:
	@$(GO) install $(GO_LDFLAGS) $(BUILDV) $(BUILDTAGS)

clean:
	$(GO) clean
	rm -f rdfm-artifact-darwin rdfm-artifact-linux rdfm-artifact-windows.exe

test:
	$(GO) test -v $(PKGS)

.PHONY: build clean test
