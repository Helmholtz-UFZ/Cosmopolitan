# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

ENV MPLCONFIGDIR=/python_docker/cosmopolitan/.config/matplotlib
ENV PATH=$PATH:/home/appuser/minio-binaries/

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
        curl && \
    rm -rf /var/lib/apt/lists/*

# Install minio client
RUN curl https://dl.min.io/client/mc/release/linux-amd64/mc --create-dirs -o /home/appuser/minio-binaries/mc && \
    chmod +x /home/appuser/minio-binaries/mc && \
    chown -R appuser:appuser /home/appuser/minio-binaries

# Set up Python environment
RUN pip install --upgrade pip && pip install poetry

WORKDIR /python_docker/cosmopolitan

# Set up matplotlib directory
RUN mkdir -p $MPLCONFIGDIR && \
    chmod 777 $MPLCONFIGDIR

ENV PYTHONPATH=/python_docker/cosmopolitan/

# Copy dependency files
COPY --chown=appuser:appuser . .
# COPY --chown=appuser:appuser poetry.lock pyproject.toml README.md ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Switch to non-root user
USER appuser

# Copy application code

CMD if [ "$GUNICORN" = 1 ] ; then \
        gunicorn -w 4 -b 0.0.0.0:$FLASK_PORT cosmopolitan_app.cosmopolitan_web_server:app; \
    else \
        python3 /python_docker/cosmopolitan/cosmopolitan_app/cosmopolitan_web_server.py; \
    fi
