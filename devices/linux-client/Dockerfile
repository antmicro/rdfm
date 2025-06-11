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
    && apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG GOVERSION="go1.22.3"
WORKDIR /opt/${GOVERSION}/
ADD https://go.dev/dl/${GOVERSION}.linux-amd64.tar.gz /opt/${GOVERSION}/
RUN tar xzf /opt/${GOVERSION}/${GOVERSION}.linux-amd64.tar.gz
ENV PATH="$PATH:/opt/${GOVERSION}/go/bin"

RUN useradd -u 1000 rdfm-builder
RUN mkdir /home/rdfm-builder
RUN chown rdfm-builder:rdfm-builder /home/rdfm-builder
