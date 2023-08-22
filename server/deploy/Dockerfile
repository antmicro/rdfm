FROM python:3.11.4-bookworm
# This Dockerfile assumes that the build starts with the current
# directory set to the monorepository root

# Install dependencies
RUN apt -qq -y update && \
        apt -qq -y install --no-install-recommends \
            curl \
            openssl && \
        apt-get autoclean && \
        apt-get clean && \
        apt-get -y autoremove && \
        rm -rf /var/lib/apt/lists/*
RUN pip3 install poetry
RUN export PATH="/root/.local/bin:${PATH}"
RUN pip3 install --upgrade pip

# Copy all sources
# We do this after installing the main dependencies to avoid
# unnecessary reinstalls
COPY . /rdfm/
WORKDIR /rdfm/server/deploy

# Build and install rdfm-server, this also pulls in any
# required Python dependencies
RUN poetry build
RUN poetry install

CMD [ "/rdfm/server/deploy/docker-entrypoint.sh" ]

