FROM node:22.10.0 AS build

# The built frontend should land in this volume, look `frontend/docker-entrypoint.sh`
VOLUME [ "/static" ]

COPY . /build
WORKDIR /build/frontend

CMD [ "/build/frontend/docker-entrypoint.sh" ]
