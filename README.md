<div>
<h1 align="center">COSMOPOLITAN</h1>
<h2 align="center"><strong>COS</strong><small>mic ray based soil </small><strong>MO</strong><small>isture </small><strong>P</strong><small>redicti</small><strong>O</strong><small>n </small><strong>LI</strong><small>ve </small><strong>T</strong><small>ree </small><strong>AN</strong><small>alysis</small></h2>
<p align="center">
	<img src="cosmopolitan_app/static/start_banner.png" alt="Welcome" width="30%">
</p>
</div>

This is a web service for analyzing cosmic ray data to predict soil moisture content. The prediction is based on a random forest model and aims to provide a live soil moisture map of Germany.

The model was developed by Ségolène Dega and the scripts are available in this [repository](https://git.ufz.de/dega/sm_prediction).

## Architecture

The web service is built as a Dash web application with the following key components:

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

### Data Flow

1. Users submit prediction jobs through web forms
2. Jobs are stored in PostgreSQL
3. Jobs are queued to Celery workers for background processing
4. Prediction models (from external `soil-moisture-prediction` library) process data
5. Results are stored in object storage and displayed through web interface

### Background Task Processing

The application uses **Celery** for distributed background task processing:

- **Message Broker**: PostgreSQL database (same as main DB)
- **Task Queues**: Separate queues for computation jobs and maintenance tasks
- **Workers**: Dedicated worker containers process tasks independently
- **Monitoring**: All worker activity logged to PostgreSQL database
- **Scheduling**: Periodic tasks for cleanup and data updates using Celery Beat

#### Task Types

- **Computation Tasks**: Soil moisture prediction jobs submitted by users
- **Maintenance Tasks**: Periodic cleanup of old jobs and CRNS data updates

## Development

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

The application runs in multiple containers:

- **webserver**: Dash web application (job submission interface)
- **worker**: Celery worker for background task processing
- **postgres**: Database with PostGIS and Celery broker tables
- **minio**: Object storage for job files
- **mailhog**: Email testing service

```bash
# Start all services (uses PyPI soil-moisture-prediction)
docker compose up --build
```

#### Local soil-moisture-prediction Development

To develop with a local version of the `soil-moisture-prediction` package instead of the
PyPI version:

```bash
# Use local package for development
docker compose -f docker-compose.yml -f docker-compose.local_smp.yml up --build

# Stop services
docker compose -f docker-compose.yml -f docker-compose.local_smp.yml down
```

**Requirements:**

- Local `soil-moisture-prediction` repository at `/home/andersj/git/soil-moisture-prediction`
- Or set `SOIL_MOISTURE_PREDICTION_PATH` environment variable to custom path

**Example with custom path:**

```bash
export SOIL_MOISTURE_PREDICTION_PATH=/path/to/your/soil-moisture-prediction
docker compose -f docker-compose.yml -f docker-compose.local_smp.yml up --build
```

**Features:**

- Live development: Changes to soil-moisture-prediction code are immediately available
- Same environment: Both webserver and worker use the local package
- Easy switching: Use regular `docker compose up` to return to PyPI version

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

## External Services

The web service relies on external services:

1. **Mail server**: [MailHog](https://github.com/mailhog/MailHog) service is used to catch emails during development
2. **PostgreSQL Database**: PostGIS-enabled database for spatial data storage
3. **MinIO**: Object storage for job files and results
4. **TimeIO API**: Source for cosmic ray neutron sensor data

## Deployment

Production deployment uses Docker containers:

- Built via GitLab CI pipeline (`.gitlab-ci.yml`)
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
