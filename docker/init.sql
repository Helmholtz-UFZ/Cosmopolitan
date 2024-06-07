-- init.sql

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
    files BYTEA[],
    file_names VARCHAR[],
    submitted BOOL,
    email VARCHAR,
    notified_end BOOL,
    logs VARCHAR,
    status VARCHAR,
    version DECIMAL
);

-- SELECT job_id, start_date FROM jobs;
-- SELECT job_id, status FROM jobs;
-- SELECT job_id, cluster_job_id FROM jobs;
-- psql -U somweb_prod_adm -p 5432 -h postgres.intranet.ufz.de -d somweb_prod
-- psql -U somweb_stage_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_stage
-- psql -U somweb_stage_rw -p 5432 -h localhost -d somweb_stage
