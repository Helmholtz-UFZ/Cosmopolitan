# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

ENV MPLCONFIGDIR=/python_docker/cosmopolitan/.config/matplotlib
ENV PATH=$PATH:/home/appuser/rclone-binaries/

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

# Set up Python environment
RUN pip install --upgrade pip && pip install poetry

WORKDIR /python_docker/cosmopolitan

# Set up matplotlib directory
RUN mkdir -p $MPLCONFIGDIR && \
    chmod 777 $MPLCONFIGDIR

ENV PYTHONPATH=/python_docker/cosmopolitan/

# Copy dependency files
COPY --chown=appuser:appuser . .

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Switch to non-root user
USER appuser

# Worker-specific command with conditional debug mode
CMD echo "Starting Celery worker in PRODUCTION mode..."; \
    python3 /python_docker/cosmopolitan/cosmopolitan_app/object_storage_manager.py setup_remote; \
    exec celery -A cosmopolitan_app.background_job_manager.celery worker \
        --loglevel=debug \
        --concurrency=4 \
        --queues=default,computation,maintenance \
        --hostname=worker@%h \
        --without-gossip \
        --without-mingle;
