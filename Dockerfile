# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

ARG GIT_PAT_SM
ARG PORT
ENV env_port=$PORT
ARG GUNICORN
ENV env_gunicorn=$GUNICORN

EXPOSE $PORT

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install git libpq-dev gcc
# RUN apt-get -y install git

WORKDIR /python_docker/cosmopolitan

RUN mkdir /python_docker/sm_prediction

ENV PYTHONPATH=/python_docker/sm_prediction/:/python_docker/cosmopolitan/

# RUN git clone https://dega:${GIT_PAT_SM}@git.ufz.de/dega/sm_prediction.git
RUN git clone \
	-b logging_optional --single-branch \
	https://dega:${GIT_PAT_SM}@git.ufz.de/dega/sm_prediction.git \
	/python_docker/sm_prediction

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
COPY .env_dep .env

CMD if [ "$env_gunicorn" = 1 ] ; then \
        gunicorn -w 4 -b 0.0.0.0:$env_port cosmopolitan_app.cosmopolitan_web_server:app; \
    else \
        python3 /python_docker/cosmopolitan/cosmopolitan_app/cosmopolitan_web_server.py; \
    fi
