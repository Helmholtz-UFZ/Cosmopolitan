# syntax=docker/dockerfile:1

FROM python:3.10-slim-bookworm

WORKDIR /python-docker

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install libpq-dev gcc
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ENV DEBUG=False
ENV PYTHONPATH=/python-docker
COPY . .
COPY .env_dep .env
# VOLUME /python-docker
# docker run -v /local/path:/python-docker -e DEBUG=True
CMD [ "python3", "./cosmopolitan_app/cosmopolitan_web_server.py"]
