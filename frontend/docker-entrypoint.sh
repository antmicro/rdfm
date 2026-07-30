#!/usr/bin/env bash

env | grep VITE > .env
npm i
npm run build
cp -r dist/* /static/
