-- =====================================================================
-- Job Application Tracker - Database Creation Script
-- Target: MySQL 8.0+ (also runs on MariaDB 10.5+)
--
-- Run with either:
--   python init_db.py            (uses the settings in your .env file)
--   mysql -u root -p < schema.sql
--
-- WARNING: this script drops and recreates the job_tracker database.
-- =====================================================================

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE job_tracker;

-- ---------------------------------------------------------------------
-- companies: organizations the user is interested in
-- ---------------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    CONSTRAINT uq_company_name UNIQUE (company_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- jobs: positions posted by a company
--   requirements (JSON) = array of skill strings, e.g. ["Python", "SQL"]
-- ---------------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_salary_range
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
    CONSTRAINT chk_salary_positive
        CHECK ((salary_min IS NULL OR salary_min >= 0) AND (salary_max IS NULL OR salary_max >= 0))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- applications: the user's application to a specific job
--   interview_data (JSON) = array of interview rounds, e.g.
--   [{"date": "2026-11-20", "type": "Phone", "interviewer": "Ana", "notes": "..."}]
-- ---------------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- contacts: people the user knows at a company (recruiters, etc.)
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Helpful indexes for the filters used in the app
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_date ON applications(application_date);

-- ---------------------------------------------------------------------
-- View: one row per application with its job and company details
-- (used by the Applications page and handy for reporting)
-- ---------------------------------------------------------------------
CREATE VIEW application_overview AS
SELECT a.application_id,
       a.application_date,
       a.status,
       a.resume_version,
       a.cover_letter_sent,
       a.interview_data,
       j.job_id,
       j.job_title,
       j.job_type,
       c.company_id,
       c.company_name
FROM applications a
JOIN jobs j      ON a.job_id = j.job_id
JOIN companies c ON j.company_id = c.company_id;

-- =====================================================================
-- Sample data (dates are relative to today so the demo always looks current)
-- =====================================================================

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp', 'Software', 'https://techcorp.example.com', 'Miami', 'FL', 'Fast-growing SaaS company. Hybrid schedule.'),
('DataCo', 'Data & Analytics', 'https://dataco.example.com', 'Orlando', 'FL', 'Analytics consultancy with many entry-level roles.'),
('BrightPath Health', 'Healthcare', 'https://brightpath.example.com', 'Tampa', 'FL', 'Hospital network building an internal software team.'),
('Sunshine FinTech', 'Finance', 'https://sunshinefintech.example.com', 'Fort Lauderdale', 'FL', 'Payments startup. Met a recruiter at the FIU career fair.'),
('Everglade Labs', 'Research', 'https://evergladelabs.example.com', 'Boca Raton', 'FL', 'Environmental data research lab.'),
('Bayside Media', 'Media', 'https://baysidemedia.example.com', 'Miami Beach', 'FL', NULL);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer', 'Full-time', 75000, 95000, 'https://techcorp.example.com/careers/101', CURDATE() - INTERVAL 30 DAY, '["Python", "SQL", "Flask"]'),
(2, 'Data Analyst', 'Full-time', 60000, 75000, 'https://dataco.example.com/jobs/7', CURDATE() - INTERVAL 25 DAY, '["Python", "SQL", "Tableau"]'),
(1, 'Frontend Developer Intern', 'Internship', 40000, 48000, 'https://techcorp.example.com/careers/115', CURDATE() - INTERVAL 20 DAY, '["HTML", "CSS", "JavaScript", "React"]'),
(3, 'Junior Backend Engineer', 'Full-time', 70000, 85000, 'https://brightpath.example.com/careers/be-1', CURDATE() - INTERVAL 18 DAY, '["Python", "Flask", "MySQL", "REST APIs", "Git"]'),
(4, 'QA Automation Engineer', 'Contract', 55000, 70000, 'https://sunshinefintech.example.com/jobs/qa', CURDATE() - INTERVAL 15 DAY, '["Python", "Selenium", "Git", "SQL"]'),
(5, 'Research Data Assistant', 'Part-time', 30000, 38000, 'https://evergladelabs.example.com/jobs/rda', CURDATE() - INTERVAL 12 DAY, '["Excel", "Python", "Statistics"]'),
(4, 'Database Developer', 'Full-time', 80000, 100000, 'https://sunshinefintech.example.com/jobs/db', CURDATE() - INTERVAL 9 DAY, '["SQL", "MySQL", "Database Design", "Python"]'),
(6, 'Web Content Developer', 'Part-time', 35000, 45000, 'https://baysidemedia.example.com/jobs/web', CURDATE() - INTERVAL 6 DAY, '["HTML", "CSS", "WordPress"]'),
(2, 'Business Intelligence Intern', 'Internship', NULL, NULL, 'https://dataco.example.com/jobs/12', CURDATE() - INTERVAL 3 DAY, '["SQL", "Power BI", "Excel"]');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, CURDATE() - INTERVAL 26 DAY, 'Interview', 'v3-software', TRUE,
    JSON_ARRAY(
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() - INTERVAL 14 DAY, '%Y-%m-%d'), 'type', 'Phone', 'interviewer', 'Maria Lopez', 'notes', 'Recruiter screen. Went well.'),
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() + INTERVAL 3 DAY, '%Y-%m-%d'), 'type', 'Technical', 'interviewer', 'James Carter', 'notes', 'Live coding in Python + SQL.')
    )),
(2, CURDATE() - INTERVAL 22 DAY, 'Screening', 'v2-data', FALSE,
    JSON_ARRAY(
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() + INTERVAL 5 DAY, '%Y-%m-%d'), 'type', 'Video', 'interviewer', 'Priya Shah', 'notes', 'Intro call with hiring manager.')
    )),
(3, CURDATE() - INTERVAL 17 DAY, 'Rejected', 'v3-software', TRUE, JSON_ARRAY()),
(4, CURDATE() - INTERVAL 14 DAY, 'Offer', 'v3-software', TRUE,
    JSON_ARRAY(
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() - INTERVAL 9 DAY, '%Y-%m-%d'), 'type', 'Video', 'interviewer', 'Dr. Allen Brooks', 'notes', 'Behavioral round.'),
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() - INTERVAL 5 DAY, '%Y-%m-%d'), 'type', 'Onsite', 'interviewer', 'Engineering team', 'notes', 'System design + team lunch.')
    )),
(5, CURDATE() - INTERVAL 12 DAY, 'Applied', 'v2-qa', FALSE, JSON_ARRAY()),
(6, CURDATE() - INTERVAL 10 DAY, 'Withdrawn', 'v2-data', FALSE, JSON_ARRAY()),
(7, CURDATE() - INTERVAL 7 DAY, 'Interview', 'v4-database', TRUE,
    JSON_ARRAY(
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() + INTERVAL 8 DAY, '%Y-%m-%d'), 'type', 'Panel', 'interviewer', 'Kevin Nguyen', 'notes', 'Prepare normalization + indexing examples.')
    )),
(9, CURDATE() - INTERVAL 2 DAY, 'Applied', 'v2-data', TRUE, JSON_ARRAY());

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Maria Lopez', 'Technical Recruiter', 'maria.lopez@techcorp.example.com', '305-555-0142', 'https://www.linkedin.com/in/example-maria-lopez', 'Handled my phone screen.'),
(1, 'James Carter', 'Engineering Manager', 'james.carter@techcorp.example.com', NULL, NULL, 'Will run the technical interview.'),
(2, 'Priya Shah', 'Analytics Manager', 'priya.shah@dataco.example.com', '407-555-0177', 'https://www.linkedin.com/in/example-priya-shah', NULL),
(3, 'Dr. Allen Brooks', 'Director of Engineering', 'abrooks@brightpath.example.com', '813-555-0110', NULL, 'Sent thank-you email after onsite.'),
(4, 'Kevin Nguyen', 'Data Platform Lead', 'kevin@sunshinefintech.example.com', '954-555-0199', 'https://www.linkedin.com/in/example-kevin-nguyen', 'Met at FIU career fair.'),
(5, 'Laura Kim', 'Lab Coordinator', 'lkim@evergladelabs.example.com', NULL, NULL, NULL);
