DESTDIR ?= /
prefix ?= $(DESTDIR)
bindir=/usr/bin
sysconfdir ?= /etc

GO ?= go
GOFMT ?= gofmt
V ?=
PKGS = $(shell go list ./... | grep -v vendor)
PKGFILES = $(shell find . \( -path ./vendor -o -path ./Godeps \) -prune \
		-o -type f -name '*.go' -print)
PKGFILES_notest = $(shell echo $(PKGFILES) | tr ' ' '\n' | grep -v '\(client/test\|_test.go\)' )
GOCYCLO ?= 15

CGO_ENABLED=1
export CGO_ENABLED

# Get rid of useless warning in lmdb
CGO_CFLAGS ?= -Wno-implicit-fallthrough -Wno-stringop-overflow
export CGO_CFLAGS

VERSION = $(shell git describe --tags --dirty --exact-match 2>/dev/null || git rev-parse --short HEAD)

GO_LDFLAGS = \
	-ldflags "-X github.com/antmicro/rdfm/conf.Version=$(VERSION)"

BUILDER_IMAGE_TAG = antmicro/rdfm-client-builder:latest
DEMO_CLIENT_TAG = antmicro/rdfm-linux-demo-client:latest

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
	$(GO) build \
		$(GO_LDFLAGS) $(BUILDV) $(BUILDTAGS) \
		-trimpath

rdfm: build

docker-builder:
	docker build -f Dockerfile -t $(BUILDER_IMAGE_TAG) .

docker-demo-client: docker-builder
	docker build -f Dockerfile.demo-client -t $(DEMO_CLIENT_TAG) .

install: install-bin \
	install-conf

install-bin: rdfm
	install -m 755 -d $(prefix)$(bindir)
	install -m 755 rdfm $(prefix)$(bindir)/

install-conf:
	install -m 755 -d $(prefix)$(sysconfdir)/rdfm
	echo "artifact_name=unknown" > $(prefix)$(sysconfdir)/rdfm/artifact_info

uninstall: uninstall-bin \
	uninstall-conf

uninstall-bin:
	rm -f $(prefix)$(bindir)/rdfm
	-rmdir -p $(prefix)$(bindir)

uninstall-conf:
	rm -f $(prefix)$(sysconfdir)/rdfm/artifact_info
	-rmdir -p $(prefix)$(sysconfdir)/rdfm

clean:
	$(GO) clean
	rm -f coverage.txt

test:
	$(GO) test $(BUILDV) $(PKGS)

.PHONY: build
.PHONY: docker-builder
.PHONY: docker-demo-client
.PHONY: clean
.PHONY: test
.PHONY: install
.PHONY: install-bin
.PHONY: install-conf
.PHONY: uninstall
.PHONY: uninstall-bin
.PHONY: uninstall-conf
