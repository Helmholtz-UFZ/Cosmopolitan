"""Celery configuration for COSMOPOLITAN background tasks."""

from cosmopolitan_app.config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT


def _get_redis_port():
    """Get Redis port, handling GitLab CI service link format."""
    port = REDIS_PORT
    # GitLab CI may set REDIS_PORT as 'tcp://redis:6379' format
    if port and port.startswith("tcp://"):
        # Extract port from URL format
        port = port.split(":")[-1]
    return port


class CeleryConfig:
    """Celery configuration class."""

    # Build Redis URL with optional password
    _redis_auth = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
    _redis_port = _get_redis_port()
    _redis_url = f"redis://{_redis_auth}{REDIS_HOST}:{_redis_port}/{REDIS_DB}"

    # Broker settings - Redis
    broker_url = _redis_url

    # Result backend - Redis
    result_backend = _redis_url

    # Task settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "Europe/Berlin"
    enable_utc = True

    # Result backend settings
    result_expires = 3600  # 1 hour
    result_persistent = True

    # Task routing
    task_routes = {
        "cosmopolitan_app.tasks.computation_tasks.*": {"queue": "computation"},
        "cosmopolitan_app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    }

    # Default queue settings
    task_default_queue = "default"
    task_default_exchange = "default"
    task_default_exchange_type = "direct"
    task_default_routing_key = "default"

    # Worker settings
    worker_prefetch_multiplier = 1  # Disable prefetching for fair distribution
    task_acks_late = True  # Acknowledge tasks after completion
    # Restart worker after 50 tasks (memory cleanup)
    worker_max_tasks_per_child = 50

    # Memory management settings
    worker_max_memory_per_child = 512000  # 512MB per worker process
    # Note: For global memory management across all workers, we need custom monitoring
    # This can be implemented in the BackgroundJobManager with Docker container limits

    # Retry settings
    task_retry_delay = 60  # 1 minute
    task_max_retries = 3

    # Task time limits
    task_soft_time_limit = 3600  # 1 hour soft limit
    task_time_limit = 3900  # 65 minutes hard limit

    # Logging - Disable Celery's logging to use our PostgreSQL logging
    worker_hijack_root_logger = False  # Don't hijack root logger
    worker_log_color = False  # Disable color for database logging
    worker_redirect_stdouts = False  # Don't redirect stdout/stderr
    worker_redirect_stdouts_level = "INFO"

    # Let our custom logging configuration handle everything
    task_track_started = True  # Track when tasks start
    task_send_sent_event = True  # Send task sent events

    # Beat scheduler settings
    beat_schedule_filename = (
        "/tmp/celerybeat-schedule"  # Use tmp directory to avoid permission issues
    )


# Global memory management constants
GLOBAL_MEMORY_LIMIT_MB = 2048  # 2GB total for all workers
MEMORY_CHECK_INTERVAL = 30  # Check every 30 seconds
