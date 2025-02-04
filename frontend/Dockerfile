FROM node:22.10.0 AS build

ARG setup_file=docker-compose.full.env

COPY . /build
WORKDIR /build/frontend
RUN set -a && . /build/$setup_file && set +a && env | grep VITE > .env
RUN npm i && npm run build

FROM nginx:1.27.2-alpine

COPY --from=build /build/frontend/dist /etc/nginx/html
