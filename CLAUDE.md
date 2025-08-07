# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

COSMOPOLITAN is a web service for analyzing cosmic ray data to predict soil moisture content using random forest models. The application aims to provide a live soil moisture map of Germany based on cosmic ray neutron sensor (CRNS) data.

## Architecture

The application is built as a Dash web application with the following key components:

- **Web Framework**: Dash (plotly) with Flask server backend
- **Database**: PostgreSQL with PostGIS extension for spatial data
- **Object Storage**: MinIO for file storage with rclone integration
- **Background Tasks**: APScheduler for periodic data updates and cleanup
- **External Services**: MailHog for email testing, TimeIO API for CRNS data

### Core Modules

- `app.py` - Main application entry point with Dash app initialization
- `postgres_manager.py` - Database ORM models and operations using SQLAlchemy
- `object_storage_manager.py` - Object storage management via rclone
- `timeio_manager.py` - Integration with TimeIO API for CRNS measurements
- `pages/` - Individual page components for the multi-page application
- `job.py` - Job processing and workflow management
- `form_factory.py` - Dynamic form generation from Pydantic models

### Data Flow

1. Users submit prediction jobs through web forms
2. Jobs are stored in PostgreSQL with spatial geometry data
3. Background tasks fetch CRNS data from TimeIO API
4. Prediction models (from external `soil-moisture-prediction` library) process data
5. Results are stored in object storage and displayed through web interface

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
```bash
# Start all services
docker compose up

# Start only the web service (requires external services)
docker compose up --no-log-prefix cosmopolitan
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
   def show_loading(n_clicks):
       """Show loading overlay when button is clicked."""
       return any(n_clicks for n_clicks in [n_clicks] if n_clicks)
   ```
   
   **Note**: If the `show_loading` callback has identical inputs to your main callback, you must add a dummy input to differentiate them:
   ```python
   # Add a dummy store to the layout
   layout = [
       dcc.Store(id="dummy_store", data=0),
       # ... rest of layout
   ]
   
   # Include dummy input in show_loading callback
   @callback(
       Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
       Input("button_id", "n_clicks"),
       Input("dummy_store", "data"),  # Dummy input
       prevent_initial_call=True,
   )
   def show_loading(n_clicks, dummy_data):
       return any(n_clicks for n_clicks in [n_clicks] if n_clicks)
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