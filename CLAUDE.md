# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in
this repository.

## Project Overview

COSMOPOLITAN is a web service for analyzing cosmic ray data to predict soil moisture
content using random forest models. The application aims to provide a live soil moisture
map of Germany based on cosmic ray neutron sensor (CRNS) data.

## Architecture

The application is built as a Dash web application with the following key components:

- **Web Framework**: Dash (plotly) with Flask server backend
- **Database**: PostgreSQL with PostGIS extension for spatial data
- **Object Storage**: MinIO for file storage with rclone integration
- **Background Tasks**: Celery with PostgreSQL broker for distributed task processing
- **External Services**: MailHog for email testing, TimeIO API for CRNS data

### Core Modules

- `app.py` - Main application entry point with Dash app initialization
- `postgres_manager.py` - Database ORM models and operations using SQLAlchemy
- `object_storage_manager.py` - Object storage management via rclone
- `timeio_manager.py` - Integration with TimeIO API for CRNS measurements
- `pages/` - Individual page components for the multi-page application
- `job.py` - Job processing and workflow management
- `form_factory.py` - Dynamic form generation from Pydantic models
- `background_job_manager.py` - Celery task management and job orchestration
- `tasks/` - Celery task definitions for computation and maintenance
  - `computation_tasks.py` - Soil moisture prediction job processing
  - `maintenance_tasks.py` - Periodic cleanup and database updates

### Data Flow

1. Users submit prediction jobs through web forms
2. Jobs are stored in PostgreSQL with spatial geometry data
3. Jobs are queued to Celery workers for background processing
4. Background tasks fetch CRNS data from TimeIO API via periodic Celery tasks
5. Prediction models (from external `soil-moisture-prediction` library) process data
6. Results are stored in object storage and displayed through web interface

### Background Task Processing

The application uses **Celery** for distributed background task processing:

#### Architecture

- **Message Broker**: PostgreSQL database (reuses existing connection)
- **Result Backend**: PostgreSQL database (stores task results and metadata)
- **Task Queues**:
  - `computation` - User-submitted soil moisture prediction jobs
  - `maintenance` - Periodic cleanup and data update tasks
  - `default` - General purpose tasks
- **Workers**: Dedicated Docker containers process tasks independently
- **Scheduling**: Celery Beat scheduler runs in the webserver's Gunicorn master process
  - Gunicorn uses `--preload` flag to ensure single Beat instance
  - Maintenance tasks scheduled at 3 AM (cleanup) and 4 AM (database updates)
  - Beat scheduler lifecycle tied to webserver container

#### Task Management

- **Lazy Initialization**: BackgroundJobManager only loads when needed
- **Database Logging**: All worker activity logged to PostgreSQL `logs` table
- **Error Handling**: Automatic retries with exponential backoff
- **Memory Management**: Workers restart after processing tasks to prevent memory leaks
- **Task Tracking**: Jobs table includes `celery_task_id` for cross-referencing

#### Key Components

- `BackgroundJobManager`: Main interface for task submission and management
- `CeleryConfig`: Configuration class with PostgreSQL broker settings
- Task modules organized by function (computation vs maintenance)
- Signal handlers for worker process initialization and logging setup

## Development Commands

### Quick Start

```bash
# Mock development (no external services)
./dev_up.sh mock

# Production development (requires credentials)
cp env_dev_prod env_dev_prod_priv
# Edit credentials in env_dev_prod_priv
./dev_up.sh prod
```

### Docker Development

The application runs in multiple containers with separate concerns:

- **webserver**: Dash web application (job submission, UI)
- **worker**: Celery worker for background task processing
- **postgres**: Database with PostGIS and Celery broker/result backend
- **minio**: Object storage for job files
- **mailhog**: Email testing service

```bash
# Start all services (uses PyPI soil-moisture-prediction)
docker compose up --build

# Start in background
docker compose up -d --build

# View logs from specific service
docker compose logs -f worker
docker compose logs -f webserver

# Stop all services
docker compose down
```

#### Worker Development Features

The worker container includes several development-friendly features:

**Auto-reload on Code Changes** (when `FLASK_DEBUG=1`):

- Automatic restart when Python files change
- Uses `watchdog` library to monitor `cosmopolitan_app/` directory
- Reduced concurrency (2 workers) for easier debugging
- Solo execution pool for deterministic debugging

**Database Logging**:

- All worker logs stored in PostgreSQL `logs` table
- Same logging configuration as webserver for consistency
- Filtered noisy loggers (file watchers, library internals)
- Structured logs with PID, timestamp, and module information

**Memory Management**:

- 2GB container memory limit
- Workers restart after processing tasks to prevent memory leaks
- Configurable memory limits per worker process

#### Local soil-moisture-prediction Development

For developing with a local version of the `soil-moisture-prediction` package:

```bash
# Use local package for development
docker compose -f docker-compose.yml -f docker-compose.local_smp.yml up --build

# Stop services
docker compose -f docker-compose.yml -f docker-compose.local_smp.yml down
```

**Setup Requirements:**

- Local `soil-moisture-prediction` repository at `/home/andersj/git/soil-moisture-prediction`
- Or set `SOIL_MOISTURE_PREDICTION_PATH` environment variable

**Custom path example:**

```bash
export SOIL_MOISTURE_PREDICTION_PATH=/path/to/your/soil-moisture-prediction
docker compose -f docker-compose.yml -f docker-compose.local_smp.yml up --build
```

**Development Benefits:**

- **Live changes**: Modifications to soil-moisture-prediction immediately available
- **Consistent environment**: Both webserver and worker use local package
- **Easy switching**: Return to PyPI version with regular `docker compose up`
- **Full debugging**: Can add breakpoints/logging in core prediction logic

#### Celery Task Debugging

**Monitor task execution:**

```bash
# Watch worker logs in real-time
docker compose logs -f worker

# Check task status in database
# Connect to postgres and query celery_taskmeta table
```

**Manual task management:**

```python
# In Python shell within container
from cosmopolitan_app.background_job_manager import get_background_job_manager

job_manager = get_background_job_manager()

# Get task status
status = job_manager.get_job_status("task-id-here")

# Cancel running task
job_manager.revoke_job("task-id-here", terminate=True)
```

### Testing

```bash
# Run full test suite with temporary services
./run_pytest.sh

# Manual pytest (requires services running)
pytest -s
```

### Code Quality

```bash
# Format code
poetry run black .
poetry run isort --profile black .

# Lint code
poetry run flake8 --max-line-length 88 --ignore=E203,W503

# Pre-commit hooks (recommended)
pre-commit install
pre-commit run --all-files
```

### Poetry Commands

```bash
# Install dependencies
poetry install

# Add new dependency
poetry add package-name

# Update dependencies
poetry update
```

## Environment Configuration

The application uses different environment files:

- `env_dev_mock` - Mock services for development
- `env_dev_prod_priv` - Production services with credentials (not in repo)
- `env_test` - Testing configuration
- `env_prod` - Production deployment

Key environment variables:

- `FLASK_DEBUG=1` - Enable debug mode with auto-reload
- `GUNICORN=0` - Use Flask dev server instead of Gunicorn
- `WEB_WORK_DIR` - Working directory for job files
- `OBJECT_STORAGE_*` - MinIO/S3 configuration variables
- `POSTGRES_*` - Database connection settings

## Database Schema

The application uses PostgreSQL with PostGIS for spatial data. The complete database schema is defined in `docker/init.sql`. Key tables include:

- `jobs` - Job tracking with spatial geometry columns for prediction areas
- `crns_measurements` - CRNS sensor data with composite primary key (date_time, sensor_id)
- `update_times_crns` - Tracking successful data updates
- `task_lock` - Background task locking mechanism
- `logs` - Application logging with timestamp indexing

## Deployment

Production deployment uses Docker containers:

- Built via GitLab CI pipeline (.gitlab-ci.yml)
- Uses `docker/prod.Dockerfile` for production builds
- Tagged releases created from git tags matching `^\d+.\d+.\d+` pattern
- Latest builds from main branch tagged as `latest`
- Supports scheduled builds with calendar versioning

## File Structure

- `cosmopolitan_app/` - Main application code
- `cosmopolitan_app/pages/` - Individual page components
- `cosmopolitan_app/work_dir/` - Job working directories (generated content)
- `docker/` - Docker configuration files
- `test/` - Test suite

## Global Loading Overlay

The application includes a global loading overlay defined in `layouts.py` that can be used across all pages to show loading states during long-running operations.

### Usage Pattern

1. **Import the constant**:

   ```python
   from cosmopolitan_app.constants import LOADING_OVERLAY_ID
   ```

2. **Create a callback to show the overlay** when buttons are clicked:

   ```python
   @callback(
       Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
       Input("button_id", "n_clicks"),
       prevent_initial_call=True,
   )
    def show_loading(*inputs):
        """Show loading overlay when preparing input."""
        return any(input for input in inputs if input is not None)
   ```

   **Note**: If the `show_loading` callback has identical inputs to your main callback,
   you must add a dummy input to differentiate them:

   ```python
   # Add a dummy store to the layout. Use None
   layout = [
       dcc.Store(id=PAGE_DUMMY_ID, data=None),
       # ... rest of layout
   ]

   # Include dummy input in show_loading callback
   @callback(
       Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
       Input("button_id", "n_clicks"),
       Input(PAGE_DUMMY_ID, "data"),  # Dummy input
       prevent_initial_call=True,
   )
   def show_loading(*inputs):
       """Show loading overlay when preparing input."""
       return any(input for input in inputs if input is not None)
   ```

3. **Hide the overlay** in your main callback by returning `False`:
   ```python
   @callback(
       # ... other outputs
       Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
       # ... inputs and states
   )
   def main_callback():
       # ... your logic
       return result, False  # False hides the overlay
   ```

### Example Implementation

See `pages/job_management.py` or `pages/submission.py` for complete examples.

## Important Notes

- Forms are generated dynamically using Pydantic models via `form_factory.py`
- CI/CD includes comprehensive testing with Chrome/ChromeDriver for Selenium tests
- The project uses rclone for object storage operations with MinIO backend

## General Code Guidlines

### Exception Handling Guidelines

- Use specific exception types, not bare `except Exception:`
- Only catch exceptions you can meaningfully handle or recover from
- If you must catch broadly, re-raise after logging: `except Exception: logger.error("..."); raise`
- Avoid silent failures - if an operation fails, the calling code should know

### Import Standards

- Place imports at module top unless there's a specific technical reason (circular imports, optional dependencies, lazy loading)
- Comment why imports are not at the top when moved elsewhere
- Group imports: stdlib, third-party, local modules

### Error Recovery

- Don't continue execution with undefined/invalid state after exceptions
- Return meaningful error values, raise custom exceptions, or fail fast
- Use type hints to clarify what functions return on success vs failure

### Logging Standards

The application uses a tag-based logging system to categorize log messages by functional area. This helps with filtering, monitoring, and debugging specific parts of the system.

#### Logging Tag Strategy

Use `extra={"tag": "tagname"}` parameter with all logging calls to categorize messages by functional area. Tags identify **what system component** is logging, while standard logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) indicate **severity/importance**.

**Approved Tag Categories:**

**Core Areas:**

- `webserver` - Web interface operations (Dash callbacks, page rendering, user interactions)
- `worker` - Celery worker operations (background task processing)
- `scheduler` - Celery Beat scheduled tasks (periodic maintenance)

**User Areas:**

- `job_submission` - Everything associated with job management and job forms
- `frontend` - Everything associated with Dash callbacks and UI interactions

**System Areas:**

- `time_io` - TimeIO API integration, sensor configuration, and CRNS data operations
- `database` - Database operations, queries, and connectivity
- `object_storage` - MinIO/rclone file operations (upload, download, delete)
- `email_service` - Email notifications and MailHog integration
- `maintenance` - System maintenance, cleanup operations, log rotation

#### Usage Examples

```python
# Core system operations
logging.info("Application startup completed", extra={"tag": "webserver"})
logging.error("Database connection failed", extra={"tag": "database"})

# User operations
logging.info("Job submitted successfully", extra={"tag": "job_submission"})
logging.warning("Invalid form data submitted", extra={"tag": "frontend"})

# System integration
logging.info("Fetching CRNS data from TimeIO API", extra={"tag": "time_io"})
logging.error("Failed to upload file to object storage", extra={"tag": "object_storage"})

# Maintenance operations
logging.info("Starting log cleanup", extra={"tag": "maintenance"})
```

#### Best Practices

1. **Always include a tag** - Every logging call should include `extra={"tag": "appropriate_tag"}`
2. **Use appropriate levels** - DEBUG for development info, INFO for normal operations, WARNING for recoverable issues, ERROR for failures
3. **Be consistent** - Use the same tag for related operations within a module
4. **Background jobs excluded** - Background computation jobs use file-based logging, not this tag system

#### Log Filtering

Logs can be filtered by tag in the web interface or programmatically:

```python
# Query logs for specific functional area
logs = PostgresManager.query_logs(date, sh, sm, eh, em, levels, pid=None, tag="time_io")

# Get all database-related logs
logs = PostgresManager.query_logs(date, sh, sm, eh, em, levels, tag="database")
```
