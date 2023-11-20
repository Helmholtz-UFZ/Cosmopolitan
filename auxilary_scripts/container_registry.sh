#!/bin/bash

set -e

version="0.0.1"
# sudo docker login git.ufz.de:4567

docker build --no-cache -t cosmopolitan-test .
# sudo docker build --no-cache -t git.ufz.de:4567/andersj/som-web:latest -t "git.ufz.de:4567/andersj/som-web:$version" .
# sudo docker push git.ufz.de:4567/andersj/som-web:latest 
# sudo docker push "git.ufz.de:4567/andersj/som-web:$version"

# TODO get maintainer priv sm-prediciton. get access token 
