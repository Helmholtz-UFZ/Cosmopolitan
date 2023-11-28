#!/bin/bash

set -e

. .env

export PYTHONPATH=$PYTHONPATH:$SM_REPO

# shellcheck disable=SC1091
source "$PYTHON_VENV/bin/activate"

if [ $GUNICORN = 1 ]; then
    gunicorn -w 4 -b "0.0.0.0:$PORT" cosmopolitan_app.cosmopolitan_web_server:app
else
    python ./cosmopolitan_app/cosmopolitan_web_server.py
fi
