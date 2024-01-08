# syntax=docker/dockerfile:1

FROM python:3.10-slim-bookworm

ARG GIT_PAT_SM
ARG SM_BRANCH

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install git libpq-dev gcc

WORKDIR /python_docker

RUN mkdir /python_docker/cosmopolitan

RUN git clone \
	-b "$SM_BRANCH" --single-branch \
	https://dega:${GIT_PAT_SM}@git.ufz.de/dega/sm_prediction.git \
	/python_docker/sm_prediction

ENV PYTHONPATH=/python_docker/sm_prediction/:/python_docker/cosmopolitan/

RUN pip install poetry

COPY poetry.lock pyproject.toml /python_docker/cosmopolitan

RUN poetry config virtualenvs.create false 
RUN poetry install --no-interaction --no-ansi

COPY . .

CMD if [ "$GUNICORN" = 1 ] ; then \
        gunicorn -w 4 -b 0.0.0.0:$PORT cosmopolitan_app.cosmopolitan_web_server:app; \
    else \
        python3 /python_docker/cosmopolitan/cosmopolitan_app/cosmopolitan_web_server.py; \
    fi
