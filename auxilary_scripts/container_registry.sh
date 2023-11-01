#!/bin/bash

set -e

version="0.0.1"
# sudo docker login git.ufz.de:4567

sudo docker build --no-cache .
# sudo docker build --no-cache -t git.ufz.de:4567/andersj/som-web:latest -t "git.ufz.de:4567/andersj/som-web:$version" .
# sudo docker push git.ufz.de:4567/andersj/som-web:latest 
# sudo docker push "git.ufz.de:4567/andersj/som-web:$version"
