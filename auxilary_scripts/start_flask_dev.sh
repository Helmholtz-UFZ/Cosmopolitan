#!/bin/bash

export FLASK_DEBUG=1

# shellcheck disable=SC1091
source "./flask_venv/bin/activate"

flask run 
