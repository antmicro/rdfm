FROM python:3.15-slim
# This Dockerfile assumes that the build starts with the current
# directory set to the monorepository root

# Install dependencies
RUN apt -qq -y update && \
    apt -qq -y install --no-install-recommends \
        curl \
        openssl \
        libpq-dev \
        build-essential && \
    apt-get autoclean && \
    apt-get clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip && \
    pip3 install poetry && \
    pip3 cache purge

# Copy all sources
# We do this after installing the main dependencies to avoid
# unnecessary reinstalls
COPY . /rdfm/
WORKDIR /rdfm/server/deploy

RUN poetry install && \
    rm -r /root/.cache/pypoetry/artifacts /root/.cache/pypoetry/cache

CMD [ "/rdfm/server/deploy/docker-entrypoint.sh" ]

