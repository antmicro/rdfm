FROM python:3.11.4-bookworm

RUN apt -qq -y update && \
        apt -qq -y install --no-install-recommends \
            gcc \
            musl-dev \
            make \
            curl \
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
            texinfo \
            build-essential \
            xz-utils \
            binutils \
            coreutils \
            debianutils \
            libcrypto++-dev \
            rdiff \
            nodejs \
            texlive-full && \
        apt-get autoclean && \
        apt-get clean && \
        apt-get -y autoremove && \
        rm -rf /var/lib/apt/lists/*

# Install Cargo
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install poetry build tool
RUN pip3 install poetry
RUN export PATH="/root/.local/bin:${PATH}"
RUN pip3 install --upgrade pip
