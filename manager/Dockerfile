FROM python:3.11.4-bookworm
# This Dockerfile assumes that the build starts with the current
# directory set to the monorepository root

# Install dependencies
RUN apt -qq -y update && apt -qq -y install --no-install-recommends curl openssl pipx
RUN export PATH="/root/.local/bin:${PATH}"
RUN pip3 install --upgrade pip
RUN pip3 install poetry

# Copy all sources
# We do this after installing the main dependencies to avoid
# unnecessary reinstalls
COPY . /rdfm/
WORKDIR /rdfm/

# Build and install rdfm-mgmt, this also pulls in any
# required Python dependencies
RUN pip3 install -e ./common/communication
RUN pip3 install -e ./manager
