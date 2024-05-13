-- init.sql

-- Lock table for background jobs
DROP TABLE IF EXISTS task_lock;

CREATE TABLE task_lock (
    task_type VARCHAR PRIMARY KEY,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE
);

-- Health check table
DROP TABLE IF EXISTS health_check;

CREATE TABLE health_check (
    check_time TIMESTAMP PRIMARY KEY,
    status VARCHAR,
    message VARCHAR
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
    cluster_job_id VARCHAR,
    email VARCHAR,
    notified_end BOOL,
    logs VARCHAR,
    status VARCHAR,
    version DECIMAL
);

-- Create test job enty. This blocks the job_id from being inserted again by a
-- user.
-- Declare the JSON string
DO $$
DECLARE
    input_data_json JSONB := '{
        "job_id": "",
        "previous_job_id": "",
        "email": "",
        "area_x1": "",
        "area_x2": "",
        "area_y1": "",
        "area_y2": "",
        "area_res": "",
        "pred_files": "",
        "crn_files": "",
        "selected_pred_files": "",
        "selected_crn_files": "",
        "monte_carlo_iterations": "",
        "monte_carlo_simulation": "",
        "past_prediction_as_feature": "",
        "average_measurements_over_time": ""
    }';
BEGIN
    -- Create test job entry
    INSERT INTO jobs (
        job_id, 
        start_date, 
        input_data, 
        files, 
        file_names, 
        submitted, 
        cluster_job_id, 
        email, 
        notified_end, 
        logs, 
        status, 
        version
    ) VALUES (
        'valid_form_data', 
        '2020-01-01', 
        input_data_json, 
        '{1,2,3}', 
        '{"file1.txt", "file2.txt", "file3.txt"}', 
        TRUE, 
        'cluster_job_id', 
        'email', 
        TRUE, 
        'logs', 
        'status', 
        1.0
    );
END $$;

-- SELECT job_id, start_date FROM jobs;
-- SELECT job_id, status FROM jobs;
-- SELECT job_id, cluster_job_id FROM jobs;
-- psql -U somweb_prod_adm -p 5432 -h postgres.intranet.ufz.de -d somweb_prod
-- psql -U somweb_stage_adm -p 5432 -h postgres-dev.intranet.ufz.de -d somweb_stage
-- psql -U somweb_stage_rw -p 5432 -h localhost -d somweb_stage
