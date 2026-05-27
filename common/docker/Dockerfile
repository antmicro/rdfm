FROM debian:trixie

ARG POSTGRES_MAJOR_VERSION="17"
ARG GO_XDELTA_REV="main"
ARG PB_REL="https://github.com/protocolbuffers/protobuf/releases/download/v31.1/protoc-31.1-linux-x86_64.zip"
ARG PROTOC_GO_REL="google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.6"
ARG APPTAINER_REL="v1.4.3"
ARG APPTAINER_URL="https://github.com/apptainer/apptainer.git"

ENV DEBIAN_FRONTEND="noninteractive"
RUN apt-get -qq -y update && apt-get -qq -y install --no-install-recommends \
        gcc \
        musl-dev \
        make \
        curl \
	ca-certificates \
        openssl \
        pkg-config \
        netcat-openbsd \
        libssl-dev \
        libudev-dev \
        mtools \
        golang \
        liblzma-dev \
        libglib2.0-dev \
        file \
        sudo \
        locales \
        gawk \
        wget \
        git \
        diffstat \
        unzip \
        build-essential \
        xz-utils \
        binutils \
        coreutils \
        debianutils \
        libcrypto++-dev \
        rdiff \
        nodejs \
	python3 \
	python3-dev \
	python3-pip \
	python3-poetry \
	python-is-python3 \
	pipx \
	postgresql \
	postgresql-${POSTGRES_MAJOR_VERSION} \
	libpq-dev \
	telnet \
	uuid-runtime \
	xxd \
	redis-server \
	cmake \
	libseccomp-dev \
	uidmap \
	fakeroot \
	cryptsetup \
	tzdata \
	dh-apparmor \
	squashfs-tools \
	iptables \
	kcat \
	openjdk-21-jre \
	openjdk-21-jdk \
	maven \
	ripgrep \
	docker.io \
	crun \
	fuse-overlayfs \
	pigz \
	device-tree-compiler \
	ninja-build \
	iproute2 \
	git-lfs \
	&& \
	apt-get autoclean && \
        apt-get clean && \
        apt-get -y autoremove && \
        rm -rf /var/lib/apt/lists/*

# Make Postgres-related executables available in PATH
RUN ln -sf /usr/lib/postgresql/${POSTGRES_MAJOR_VERSION}/bin/initdb /bin/initdb && \
    ln -sf /usr/lib/postgresql/${POSTGRES_MAJOR_VERSION}/bin/postgres /bin/postgres

# Install XDelta
RUN git clone https://github.com/antmicro/go-xdelta xdelta && \
    (cd xdelta && \
        git checkout ${GO_XDELTA_REV} && \
        cmake -B build/ -DCGO_INTEGRATION=ON -DENCODER=ON && \
        cmake --build build/ && \
        cmake --install build/) && \
    rm -rf xdelta/

# Path to which pipx installs
ENV PATH="/root/.local/bin:${PATH}"

# Install protocol buffers for Go
WORKDIR /opt
ENV PATH="/opt/protoc/bin:${PATH}"
ENV GOBIN="/usr/bin"
RUN wget --quiet ${PB_REL} && \
    unzip $(basename ${PB_REL}) -d protoc && \
    rm -f $(basename ${PB_REL}) && \
    go install ${PROTOC_GO_REL} && \
    rm -rf /root/.cache && rm -rf /root/go/pkg

# Install apptainer
WORKDIR /opt
RUN git clone ${APPTAINER_URL} && cd apptainer && \
    git checkout ${APPTAINER_REL} && ./mconfig --without-suid && \
    cd builddir && make && make install && cd && rm -rf /opt/apptainer && \
    rm -rf /root/.cache && rm -rf /root/go/pkg

WORKDIR /root

# Explicitly point to CA certificates
ENV SSL_CERT_FILE="/etc/ssl/certs/ca-certificates.crt"
ENV REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"
