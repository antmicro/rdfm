#!/usr/bin/env bash
set -e

cd "$(dirname $0)/../../documentation/"
pip3 install -r requirements.txt
make html latex
