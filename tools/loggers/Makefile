GO ?= go
bindir ?= /usr/bin
filename ?= loggers
prefix ?= $(DESTDIR)

ifeq ($(V),1)
BUILDV = -v
endif

build:
	$(GO) get
	$(GO) build $(BUILDV) \
		-trimpath \
		-o $(filename)

install: build
	install -m 755 -d $(prefix)$(bindir)
	install -m 700 $(filename) $(prefix)$(bindir)/

clean:
	rm $(filename)

.PHONY: build
.PHONY: install
.PHONY: clean
