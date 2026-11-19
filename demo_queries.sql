-- Handy queries to show the database side of the app (used in the demo video)
USE job_tracker;

SHOW TABLES;
DESCRIBE jobs;

-- Foreign keys defined in the schema
SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'job_tracker' AND REFERENCED_TABLE_NAME IS NOT NULL;

-- JSON columns
SELECT job_id, job_title, requirements FROM jobs;
SELECT application_id, status, interview_data FROM applications;

-- Everything joined together through the view
SELECT application_id, company_name, job_title, status, application_date
FROM application_overview ORDER BY application_date DESC;

-- Row counts (compare with the dashboard)
SELECT (SELECT COUNT(*) FROM companies) AS companies,
       (SELECT COUNT(*) FROM jobs) AS jobs,
       (SELECT COUNT(*) FROM applications) AS applications,
       (SELECT COUNT(*) FROM contacts) AS contacts;
