#!/bin/bash

set -e

# sudo docker login git.ufz.de:4567

sudo docker build -t git.ufz.de:4567/andersj/som-web .
sudo docker push git.ufz.de:4567/andersj/som-web
