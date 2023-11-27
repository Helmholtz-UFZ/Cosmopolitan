#!/bin/bash

export FLASK_DEBUG=1

export PYTHONPATH=$PYTHONPATH:../sm_prediction/
# shellcheck disable=SC1091
source "./flask_venv/bin/activate"
# python ./cosmopolitan_app/cosmopolitan_web_server.py
gunicorn -w 4 -b 0.0.0.0:8080 cosmopolitan_app.cosmopolitan_web_server:app
