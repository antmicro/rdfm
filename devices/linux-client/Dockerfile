FROM debian:bookworm

RUN apt-get update \
    && env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    make \
    gcc \
    g++ \
    gio-2.0 \
    liblzma-dev \
    libssl-dev \
    git \
    ca-certificates \
    cmake \
    protobuf-compiler \
    libprotobuf-dev \
    && apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG GOVERSION="go1.22.3"
WORKDIR /opt/${GOVERSION}/
ADD https://go.dev/dl/${GOVERSION}.linux-amd64.tar.gz /opt/${GOVERSION}/
RUN tar xzf /opt/${GOVERSION}/${GOVERSION}.linux-amd64.tar.gz
ENV PATH="$PATH:/opt/${GOVERSION}/go/bin"
RUN GOBIN=/opt/${GOVERSION}/go/bin go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.6
RUN useradd -u 1000 rdfm-builder

WORKDIR /tmp
RUN git clone https://github.com/antmicro/go-xdelta xdelta \
    && cd xdelta \
    && cmake -B build/ -DCGO_INTEGRATION=ON -DENCODER=ON \
    && cmake --build build/ \
    && cmake --install build/ \
    && cd ../ \
    && rm -rf /tmp/xdelta

RUN mkdir /home/rdfm-builder
RUN chown rdfm-builder:rdfm-builder /home/rdfm-builder
