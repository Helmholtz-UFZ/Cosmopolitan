# syntax=docker/dockerfile:1

FROM python:3.10-slim-bookworm

WORKDIR /python-docker

RUN apt-get update 
RUN apt-get -y install libpq-dev gcc
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
