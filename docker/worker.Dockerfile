# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

ENV MPLCONFIGDIR=/python_docker/cosmopolitan/.config/matplotlib
ENV PATH=$PATH:/home/appuser/rclone-binaries/
ENV TZ=Europe/Berlin

# Create non-root user early
RUN useradd -m -u 1000 appuser

# Install system dependencies
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install --no-install-recommends \
        git \
        libpq-dev \
        gcc \
        python3-dev \
        libc-dev \
        libcairo2-dev \
        curl \
        unzip && \
    rm -rf /var/lib/apt/lists/*

# Install rclone
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip && \
    unzip rclone-current-linux-amd64.zip && \
    mkdir -p /home/appuser/rclone-binaries && \
    cp rclone-*-linux-amd64/rclone /home/appuser/rclone-binaries/ && \
    chmod +x /home/appuser/rclone-binaries/rclone && \
    chown -R appuser:appuser /home/appuser/rclone-binaries && \
    rm -rf rclone-*

RUN rclone --version

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /python_docker/cosmopolitan

# Set up matplotlib directory
RUN mkdir -p $MPLCONFIGDIR && \
    chmod 777 $MPLCONFIGDIR

ENV PYTHONPATH=/python_docker/cosmopolitan/
ENV PATH="/python_docker/cosmopolitan/.venv/bin:$PATH"

# Copy dependency files
COPY --chown=appuser:appuser . .

COPY --chown=1000:1000 env_prod .env

# Install dependencies
RUN uv sync --no-dev --frozen

# Switch to non-root user
USER appuser

# `&&`, not `;`. With `;` a failing storage setup — a moved module, a bad path —
# still let Celery start, just without a configured rclone remote, and the first
# symptom was a job failing three layers away from the cause. The `exec celery`
# marker is what lets a build job run the setup step on its own; see
# docs/conventions/worker_image.md in the framework.
CMD echo "Starting Celery worker in PRODUCTION mode..." && \
    python3 -m cosmo_suite.object_storage_manager setup_remote && \
    exec celery -A cosmopolitan_app.celery_app.celery worker \
        --loglevel=debug \
        --concurrency=4 \
        --queues=default,computation,maintenance,test \
        --hostname=worker@%h \
        --without-gossip \
        --without-mingle;
