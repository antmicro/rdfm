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

VERSION = $(shell git describe --tags --dirty --exact-match 2>/dev/null || git rev-parse --short HEAD)

GO_LDFLAGS = \
	-ldflags "-X github.com/antmicro/rdfm/devices/linux-client/conf.Version=$(VERSION)"

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

rdfm-mcumgr-client: build

install: install-bin

install-bin: rdfm-mcumgr-client
	install -Dm 755 -t $(prefix)$(bindir) rdfm-mcumgr-client 

uninstall: uninstall-bin

uninstall-bin:
	rm -f $(prefix)$(bindir)/rdfm-mcumgr-client
	-rmdir -p $(prefix)$(bindir)

clean:
	$(GO) clean
	rm -f coverage.txt

.PHONY: build
.PHONY: clean
.PHONY: install
.PHONY: install-bin
.PHONY: uninstall
.PHONY: uninstall-bin
