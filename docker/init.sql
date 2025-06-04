-- init.sql
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
    notified_end BOOL,
    logs VARCHAR,
    status VARCHAR,
    version VARCHAR
);

-- Create logs table for application logging
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
CREATE TABLE update_times_crns (
    update TIMESTAMP NOT NULL PRIMARY KEY,
    successful BOOLEAN NOT NULL
);

-- Table to store CRNS measurements
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
CREATE INDEX crns_measurements_geom_idx
    ON crns_measurements
    USING GIST (geom);

-- SELECT job_id, start_date FROM jobs;
-- SELECT job_id, status FROM jobs;
-- SELECT job_id, cluster_job_id FROM jobs;
-- SELECT message FROM logs WHERE timestamp > NOW() - INTERVAL '1 day';
-- psql -U somweb_prod_adm -p 5432 -h postgres.intranet.ufz.de -d somweb_prod
-- psql -U somweb_stage_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_stage
-- psql -U somweb_stage_rw -p 5432 -h localhost -d somweb_stage
