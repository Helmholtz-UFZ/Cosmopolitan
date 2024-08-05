#!/bin/bash

export DB_HOST_NAME=0.0.0.0
export EMAIL_SERVER=172.17.0.1

if [ -f .env ]; then
    mv .env .env.bak
fi

cp .env_test .env

docker rm postgres
docker compose up postgres mailhog -d

sleep 2

until docker exec postgres pg_isready -q; do
    echo "Waiting for PostgreSQL to start..."
    sleep 1
done

MAIL_HOG_PORT=${MAIL_HOG_PORT:-8025}
until $(curl --silent --output /dev/null http://localhost:${MAIL_HOG_PORT}); do
    echo "Waiting for MailHog to be available..."
    sleep 1
done

pytest -s

if [ -f .env.bak ]; then
    mv .env.bak .env
fi
docker compose down
