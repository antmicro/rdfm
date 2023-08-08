FROM debian:bookworm

RUN apt-get update \
    && env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    make \
    gcc \
    g++ \
    golang \
    gio-2.0 \
    liblzma-dev \
    libssl-dev \
    git \
    ca-certificates \
    && apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd -u 1000 rdfm-builder
RUN mkdir /home/rdfm-builder
RUN chown rdfm-builder:rdfm-builder /home/rdfm-builder
