-- init.sql

-- -- Grant connect on the database to the user
-- GRANT CONNECT ON DATABASE somweb_stage TO somweb_stage_rw;

DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS logs;

-- Create jobs table
CREATE TABLE jobs (
    job_id VARCHAR PRIMARY KEY,
    start_date DATE,
    input_data JSONB,
    files BYTEA[],
    file_names VARCHAR[],
    submitted BOOL,
    cluster_job_id VARCHAR,
    email VARCHAR,
    notified_end BOOL,
    logs VARCHAR,
    status VARCHAR,
    version DECIMAL
);

-- Create logs table
CREATE TABLE logs (
    log_id SERIAL PRIMARY KEY,
    level VARCHAR(10),
    message VARCHAR,
    timestamp TIMESTAMPTZ
);

-- Grant permissions on tables to the user
GRANT INSERT, UPDATE, DELETE ON TABLE jobs TO somweb_stage_rw;
GRANT INSERT, UPDATE, DELETE ON TABLE logs TO somweb_stage_rw;

-- GRANT INSERT, UPDATE, DELETE ON TABLE jobs TO somweb_prod_rw;
-- GRANT INSERT, UPDATE, DELETE ON TABLE logs TO somweb_prod_rw;
-- SELECT job_id, start_date FROM jobs;
-- SELECT job_id, status FROM jobs;
-- SELECT job_id, cluster_job_id FROM jobs;
-- psql -U somweb_prod_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_prod
-- psql -U somweb_stage_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_stage
-- psql -U somweb_stage_rw -p 5432 -h localhost -d somweb_stage
