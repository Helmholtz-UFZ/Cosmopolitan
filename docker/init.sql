-- init.sql
-- Database schema for COSMOPOLITAN application
--
-- This file contains all application-specific tables.
-- Celery uses Redis for both broker and result backend, no database tables needed.

CREATE EXTENSION IF NOT EXISTS postgis;

SET timezone = 'Europe/Berlin';

-- Lock table for background jobs
DROP TABLE IF EXISTS task_lock;
CREATE TABLE task_lock (
    task_type VARCHAR PRIMARY KEY,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE
);

-- Jobs table
DROP TABLE IF EXISTS jobs;
CREATE TABLE jobs (
    job_id VARCHAR PRIMARY KEY,
    start_date DATE,
    input_data JSONB,
    submitted BOOL,
    email VARCHAR,
    prepared_input BOOL,
    notified_end BOOL,
    logs VARCHAR,
    status VARCHAR,
    version VARCHAR,
    celery_task_id VARCHAR
);

-- Create logs table for application logging
DROP TABLE IF EXISTS logs;
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    pid INTEGER NOT NULL,
    level VARCHAR(10) NOT NULL,
    module VARCHAR(50) NOT NULL,
    message TEXT NOT NULL
);

--Create indexes to improve query performance
CREATE INDEX IF NOT EXISTS logs_timestamp_idx ON logs (timestamp);

-- Table to store update times and success status
DROP TABLE IF EXISTS update_times_crns;
CREATE TABLE update_times_crns (
    update DATE NOT NULL PRIMARY KEY,
    successful BOOLEAN NOT NULL
);

-- Table to store CRNS measurements
DROP TABLE IF EXISTS crns_measurements;
CREATE TABLE crns_measurements (
    date_time TIMESTAMP NOT NULL,
    sensor_id INTEGER NOT NULL,
    soil_moisture DOUBLE PRECISION,
    error_high DOUBLE PRECISION,
    error_low DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(POINT, 4326),
    sensor_name VARCHAR(255),
    representative BOOLEAN,
    PRIMARY KEY (date_time, sensor_id)
);

-- Create a spatial index on the geometry column for efficient geo queries
CREATE INDEX IF NOT EXISTS idx_crns_measurements_geom
    ON crns_measurements
    USING GIST (geom);

-- TimeIO Info table for sensor management
DROP TABLE IF EXISTS timeio_info;
CREATE TABLE timeio_info (
    sensor_id INTEGER PRIMARY KEY,
    sensor_name VARCHAR(255) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    ignored BOOLEAN DEFAULT FALSE,
    datastreams JSONB NOT NULL,
    stationary BOOLEAN GENERATED ALWAYS AS (
        NOT (
            jsonb_path_exists(datastreams, '$.* ? (@ == "longitude")') AND
            jsonb_path_exists(datastreams, '$.* ? (@ == "latitude")')
        )
    ) STORED
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS timeio_info_ignored_idx ON timeio_info (ignored);
CREATE INDEX IF NOT EXISTS timeio_info_type_idx ON timeio_info (sensor_type);
CREATE INDEX IF NOT EXISTS timeio_info_stationary_idx ON timeio_info (stationary);

-- Application configuration table
DROP TABLE IF EXISTS app_config;
CREATE TABLE app_config (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Initial configuration values (NULL means disabled/default)
INSERT INTO app_config (key, value) VALUES ('crns_start_date', NULL);
INSERT INTO app_config (key, value) VALUES ('crns_end_date', NULL);

-- Table to track update_db_task runs for log filtering
DROP TABLE IF EXISTS update_db_runs;
CREATE TABLE update_db_runs (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    pid INTEGER,
    status VARCHAR(20) DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS update_db_runs_start_time_idx ON update_db_runs (start_time DESC);

-- SELECT job_id, start_date FROM jobs;
-- SELECT job_id, status FROM jobs;
-- SELECT job_id, cluster_job_id FROM jobs;
-- SELECT email FROM jobs WHERE job_id = 'test_job_001';
-- SELECT input_data FROM jobs WHERE job_id = 'zippy_paper_orca';
-- SELECT message FROM logs WHERE timestamp > NOW() - INTERVAL '1 day';
-- SELECT * FROM update_times_crns;
-- SELECT sensor_id, date_time, latitude, longitude, soil_moisture, representative FROM crns_measurements;
-- SELECT sensor_id, date_time, latitude, longitude, soil_moisture, representative FROM crns_measurements WHERE sensor_id = 149;
-- psql -U somweb_prod_adm -p 5432 -h postgres.intranet.ufz.de -d somweb_prod
-- psql -U somweb_stage_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_stage
-- psql -U somweb_stage_rw -p 5432 -h localhost -d somweb_stage

-- ============================================================================
-- HOW TO OVERRIDE PRODUCTION DATABASE WITH THIS INIT.SQL
-- ============================================================================
-- WARNING: This will DROP all existing tables and data! Make a backup first!
--
-- 1. Create a backup of the production database:
--    pg_dump -U somweb_prod_adm -h postgres.intranet.ufz.de -d somweb_prod -F c -f backup_$(date +%Y%m%d_%H%M%S).dump
--
-- 2. Execute this init.sql file against the production database:
--    psql -U somweb_prod_adm -p 5432 -h postgres.intranet.ufz.de -d somweb_prod -f docker/init.sql
--
-- 3. Verify the tables were recreated:
--    psql -U somweb_prod_adm -p 5432 -h postgres.intranet.ufz.de -d somweb_prod -c "\dt"
--
-- For staging environment:
--    psql -U somweb_stage_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_stage -f docker/init.sql
--
-- Note: This script uses DROP TABLE IF EXISTS, so it will delete all existing data
-- ============================================================================
