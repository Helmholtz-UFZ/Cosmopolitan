# COSMOPOLITAN Webservice Documentation

### COSmic ray based soil MOisture PredictiOn LIve Tree ANalysis

*Last updated: 2025-12-11 15:42:11*

## Table of Contents
1. [Introduction](#introduction)
2. [User Workflow](#user-workflow)
3. [Administration](#administration)

---

<h2 id="introduction">Introduction</h2>

COSMOPOLITAN is a web service for analyzing cosmic ray neutron sensor (CRNS) data to
predict soil moisture content using machine learning models. The service provides tools
for submitting prediction jobs, monitoring their execution, and analyzing results
through interactive visualizations.

### How It Works

The application uses a distributed architecture to handle prediction jobs efficiently:

- **Background Processing**: Prediction jobs are processed asynchronously by Celery
  workers, allowing you to submit jobs and navigate away while processing continues.
  You can check back anytime to monitor progress and view results.

- **Database**: Job data, sensor measurements, and system logs are stored in PostgreSQL
  with PostGIS extension for spatial data queries. This enables efficient geographic
  searches and spatial analysis.

- **Object Storage**: Large result files, including prediction maps and analysis data,
  are stored in MinIO object storage for efficient retrieval and long-term archival.

- **Web Interface**: Built with the Dash framework for interactive data visualization,
  providing real-time updates, interactive maps, and responsive charts.

---

<h2 id="user-workflow">User Workflow</h2>

This section describes the typical user journey for creating and analyzing soil moisture
predictions.

### 1. Home Page

Welcome to COSMOPOLITAN - the landing page for soil moisture prediction services.

This is the home page where you start your journey. COSMOPOLITAN (COSmic ray based
soil MOisture PredictiOn LIve Tree ANalysis) is a web service that analyzes cosmic
ray neutron sensor data to predict soil moisture content using machine learning models.

From here, you can begin creating a new prediction job to analyze soil moisture data
for your area of interest.

<img src="/assets/docs/screenshots/home.png" alt="Home Page" style="max-width: 100%; height: auto;" />

**Next Step**: Create New Job →

### 2. Create New Job

Create a new soil moisture prediction job.

This page allows you to start a new prediction job by creating a unique job identifier.
The system generates a random, memorable job ID for you, but you can customize it to
something more meaningful. Each job ID must be unique and follow specific formatting
rules.

Once you've chosen your job ID, click "Prepare input" to move on to configuring your
prediction parameters and uploading data.

<img src="/assets/docs/screenshots/new_job.png" alt="Create New Job" style="max-width: 100%; height: auto;" />

**Next Step**: Job Input Form →

### 3. Job Input Form

Configure your prediction job parameters and upload input data.

This page provides a comprehensive form where you can:
- Upload cosmic ray neutron sensor (CRNS) measurement data
- Upload predictor variable files (environmental data)
- Define your prediction area by drawing on a map or uploading boundaries
- Set time ranges and other prediction parameters
- Preview your prediction area before submission

The form validates your inputs and shows a live preview of the geographic area where
soil moisture will be predicted. Once all required data is provided and validated,
you can proceed to the submission page.

<img src="/assets/docs/screenshots/input.png" alt="Job Input Form" style="max-width: 100%; height: auto;" />

**Next Step**: Job Submission →

### 4. Job Submission

Submit your job and monitor its progress.

This page serves as your job control center where you can:
- Review your job configuration and input parameters
- Submit your job for processing in the background
- Monitor job status (Pending, Running, Failed, or Completed)
- View job execution logs in real-time
- Change input parameters if needed
- Navigate to results once processing is complete
- Spawn a new job based on the current one

Jobs are processed asynchronously by background workers, so you can safely navigate
away from this page while your job runs. You'll receive status updates and can return
at any time to check progress.

<img src="/assets/docs/screenshots/submission.png" alt="Job Submission" style="max-width: 100%; height: auto;" />

**Next Step**: View Results →

### 5. View Results

View and analyze your soil moisture prediction results.

This page provides comprehensive visualization and analysis tools for your completed
prediction job:

**Interactive Maps:**
- View soil moisture predictions overlaid on geographic maps
- Switch between different map types (OpenStreetMap, satellite imagery)
- Navigate through prediction time steps
- Toggle measurement point displays
- Adjust map opacity and explore spatial patterns

**Statistical Analysis:**
- Correlation heatmaps showing relationships between variables
- Feature importance plots revealing which predictors matter most
- Statistical summaries for each time step
- Detailed performance metrics

You can explore results across multiple time periods, examine which environmental
factors most influence soil moisture predictions, and understand model performance
through various visualization tools.

<img src="/assets/docs/screenshots/results.png" alt="View Results" style="max-width: 100%; height: auto;" />

---

<h2 id="administration">Administration</h2>

Administrative pages for system management, monitoring, and configuration.

### Job Management

Manage all prediction jobs from a central dashboard.

This administrative page provides a comprehensive overview of all jobs in the system.
You can:
- View all jobs in a sortable, filterable table
- See job status, creation dates, and submission status at a glance
- Select and delete individual jobs or multiple jobs at once
- Trigger cleanup operations to remove old jobs automatically
- Access individual job pages directly from the table

The table uses color coding to quickly identify job statuses: blue for completed jobs,
green for running jobs, red for failed jobs, and grey for pending jobs. You can select
rows to perform bulk operations like deletion.

<img src="/assets/docs/screenshots/job_management.png" alt="Job Management" style="max-width: 100%; height: auto;" />

### Sensor Management

Configure and manage cosmic ray neutron sensor settings.

This administrative page lets you manage the cosmic ray neutron sensors (CRNS) that
provide measurement data for predictions. Features include:

- View all configured sensors in a comparison table
- Compare database configuration with TimeIO API data
- Add new sensors or update existing sensor configurations
- Configure sensor datastreams (measurement channels)
- Validate sensor settings and datastream formats
- Mark sensors as ignored if they shouldn't be used for predictions

Sensors can be stationary stations, trains, or rovers, each with different datastream
requirements. The page validates that sensor configurations follow the correct format
and helps ensure data quality for prediction models.

<img src="/assets/docs/screenshots/sensor_management.png" alt="Sensor Management" style="max-width: 100%; height: auto;" />

### Measurement Database

Query and explore the CRNS measurement database.

This page provides a powerful interface for exploring the cosmic ray neutron sensor
measurement data stored in the database. You can:

- Filter measurements by date range, sensor type, and geographic area
- Define search areas using coordinates or by drawing on a map
- View measurement data in a detailed, sortable table
- Generate statistical summaries of queried data
- Export filtered results to CSV format for external analysis
- Preview the geographic area covered by your query

The database contains soil moisture measurements, error estimates, coordinates, and
timestamps from various sensor types (stationary, mobile rovers, and trains). This
tool is useful for data exploration, quality checking, and understanding sensor
coverage patterns.

<img src="/assets/docs/screenshots/measurment_view.png" alt="Measurement Database" style="max-width: 100%; height: auto;" />

### CRNS Database Administration

Administer CRNS database updates and maintenance operations.

This administrative page controls how the system fetches and stores cosmic ray neutron
sensor data from the TimeIO API. Key functions include:

**Date Configuration:**
- Set the start date for data updates (when to begin fetching data)
- Optionally set an end date, or leave empty to always update to yesterday
- Configuration persists between update runs

**Update Operations:**
- Trigger manual updates to fetch latest sensor data from TimeIO API
- View update status and progress
- Monitor failed updates and error information
- See when the last successful update occurred

**Database Management:**
- Purge all measurement data from the database (requires confirmation)
- View update logs showing detailed operation history
- Refresh status information on demand

Background workers handle the actual data fetching, so updates run asynchronously.
The system typically runs automatic daily updates, but this page allows manual control
when needed.

<img src="/assets/docs/screenshots/crns_db_admin.png" alt="CRNS Database Administration" style="max-width: 100%; height: auto;" />

### Application Logs

View and filter application logs for debugging and monitoring.

This page provides access to the application's logging system, allowing you to track
system activity, debug issues, and monitor operations. You can:

- Filter logs by date and time range
- Select specific log levels (Debug, Info, Warning, Error, Critical)
- Filter by functional area using tags (job_submission, database, frontend, etc.)
- Filter by process ID to track specific worker or server processes
- View logs in a formatted, readable table
- Refresh logs on demand to see latest entries

Logs are stored in the database and include timestamps, log levels, logger names,
messages, and optional tags categorizing the log by system component. This is the
primary tool for understanding system behavior, diagnosing problems, and monitoring
background job execution.

<img src="/assets/docs/screenshots/logs.png" alt="Application Logs" style="max-width: 100%; height: auto;" />

### Worker Management

Monitor and manage background workers and tasks.

This administrative page provides real-time visibility into the Celery background task
system that processes prediction jobs and maintenance operations. Features include:

**Worker Status:**
- View active worker processes and their configuration
- See worker pool types, concurrency settings, and queue assignments
- Check worker availability and health

**Task Monitoring:**
- View currently executing tasks (active tasks)
- See tasks waiting in worker queues (reserved tasks)
- Monitor scheduled tasks waiting for their run time
- Track revoked (cancelled) tasks
- Display task details including name, arguments, and execution time

**Task Control:**
- Kill actively running tasks (forcefully terminate)
- Cancel scheduled tasks before they execute
- Confirmation dialogs prevent accidental terminations

**Status Updates:**
- Manual refresh to get latest worker and task information
- Timestamp showing when data was last refreshed

This page is essential for monitoring system load, debugging stuck tasks, and managing
resource usage during peak periods.

<img src="/assets/docs/screenshots/worker_management.png" alt="Worker Management" style="max-width: 100%; height: auto;" />

---

*Generated automatically from module docstrings*
