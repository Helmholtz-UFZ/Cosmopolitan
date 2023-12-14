# Use the official Postgres image
FROM postgres:14-alpine

# Set environment variables
ARG POSTGRES_DB
ARG POSTGRES_USER
ARG POSTGRES_PASSWORD

ENV POSTGRES_DB="$POSTGRES_DB"
ENV POSTGRES_USER="$POSTGRES_USER"
ENV POSTGRES_PASSWORD="$POSTGRES_PASSWORD"

# Copy SQL scripts to docker-entrypoint-initdb.d to execute on container startup
COPY ./docker/init.sql /docker-entrypoint-initdb.d/
