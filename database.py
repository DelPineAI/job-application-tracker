"""
database.py - All MySQL access for the Job Application Tracker.

Every function opens a short-lived connection, runs parameterized SQL
(never string-formatted user input, to prevent SQL injection), and
returns plain Python dicts/lists that the Flask templates can use.
"""

import json
import os
from contextlib import contextmanager
from datetime import date

import mysql.connector

try:  # Load DB settings from a .env file if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency
    pass


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "job_tracker"),
}

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]


# ---------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------
def get_db():
    """Open a new connection to the job_tracker database."""
    return mysql.connector.connect(**DB_CONFIG)


@contextmanager
def db_cursor(commit=False):
    """Yield a dictionary cursor; commit on success, roll back on error."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def query_all(sql, params=()):
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql, params=()):
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE. Returns the new id (INSERT) or rows affected."""
    with db_cursor(commit=True) as cur:
        cur.execute(sql, params)
        return cur.lastrowid or cur.rowcount


def parse_json(value, default=None):
    """MySQL returns JSON columns as str (or bytes); turn them into Python objects."""
    if default is None:
        default = []
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _like(term):
    return f"%{term.strip()}%"


# ---------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------
def get_all_companies(search=None):
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id)      AS job_count,
               (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.company_id) AS contact_count
        FROM companies c
    """
    params = []
    if search:
        sql += " WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s"
        params = [_like(search)] * 3
    sql += " ORDER BY c.company_name"
    return query_all(sql, params)


def get_company_choices():
    """Lightweight list used for dropdown menus."""
    return query_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


def get_company(company_id):
    return query_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))


def company_name_exists(name, exclude_id=None):
    sql = "SELECT company_id FROM companies WHERE LOWER(company_name) = LOWER(%s)"
    params = [name]
    if exclude_id:
        sql += " AND company_id <> %s"
        params.append(exclude_id)
    return query_one(sql, params) is not None


def create_company(data):
    return execute(
        """INSERT INTO companies (company_name, industry, website, city, state, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"]),
    )


def update_company(company_id, data):
    execute(
        """UPDATE companies
           SET company_name = %s, industry = %s, website = %s,
               city = %s, state = %s, notes = %s
           WHERE company_id = %s""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"], company_id),
    )


def delete_company(company_id):
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


def get_company_delete_impact(company_id):
    """How many child rows will be removed by ON DELETE CASCADE."""
    return query_one(
        """SELECT
             (SELECT COUNT(*) FROM jobs WHERE company_id = %s) AS jobs,
             (SELECT COUNT(*) FROM contacts WHERE company_id = %s) AS contacts,
             (SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id = j.job_id
               WHERE j.company_id = %s) AS applications""",
        (company_id, company_id, company_id),
    )


# ---------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------
def _prepare_job(row):
    if row:
        row["requirements"] = parse_json(row.get("requirements"))
    return row


def get_all_jobs(search=None, job_type=None, company_id=None):
    sql = """
        SELECT j.*, c.company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE 1 = 1
    """
    params = []
    if search:
        sql += " AND (j.job_title LIKE %s OR c.company_name LIKE %s)"
        params += [_like(search)] * 2
    if job_type:
        sql += " AND j.job_type = %s"
        params.append(job_type)
    if company_id:
        sql += " AND j.company_id = %s"
        params.append(company_id)
    sql += " ORDER BY j.date_posted DESC, j.job_id DESC"
    return [_prepare_job(r) for r in query_all(sql, params)]


def get_job_choices():
    return query_all(
        """SELECT j.job_id, j.job_title, c.company_name
           FROM jobs j JOIN companies c ON j.company_id = c.company_id
           ORDER BY c.company_name, j.job_title"""
    )


def get_job(job_id):
    row = query_one(
        """SELECT j.*, c.company_name
           FROM jobs j JOIN companies c ON j.company_id = c.company_id
           WHERE j.job_id = %s""",
        (job_id,),
    )
    return _prepare_job(row)


def get_jobs_for_company(company_id):
    return get_all_jobs(company_id=company_id)


def create_job(data):
    return execute(
        """INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                             job_url, date_posted, requirements)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
         data["salary_max"], data["job_url"], data["date_posted"],
         json.dumps(data["requirements"])),
    )


def update_job(job_id, data):
    execute(
        """UPDATE jobs
           SET company_id = %s, job_title = %s, job_type = %s, salary_min = %s,
               salary_max = %s, job_url = %s, date_posted = %s, requirements = %s
           WHERE job_id = %s""",
        (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
         data["salary_max"], data["job_url"], data["date_posted"],
         json.dumps(data["requirements"]), job_id),
    )


def delete_job(job_id):
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))


def get_job_delete_impact(job_id):
    return query_one(
        "SELECT COUNT(*) AS applications FROM applications WHERE job_id = %s", (job_id,)
    )


def get_all_skills():
    """Every distinct skill found in job requirements (for suggestions)."""
    skills = {}
    for row in query_all("SELECT requirements FROM jobs"):
        for skill in parse_json(row["requirements"]):
            skills.setdefault(skill.strip().lower(), skill.strip())
    return sorted(skills.values(), key=str.lower)


# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------
def _prepare_application(row):
    if row:
        row["interview_data"] = parse_json(row.get("interview_data"))
        row["cover_letter_sent"] = bool(row.get("cover_letter_sent"))
    return row


def get_all_applications(status=None, search=None, job_id=None, company_id=None):
    sql = "SELECT * FROM application_overview WHERE 1 = 1"
    params = []
    if status:
        sql += " AND status = %s"
        params.append(status)
    if search:
        sql += " AND (job_title LIKE %s OR company_name LIKE %s)"
        params += [_like(search)] * 2
    if job_id:
        sql += " AND job_id = %s"
        params.append(job_id)
    if company_id:
        sql += " AND company_id = %s"
        params.append(company_id)
    sql += " ORDER BY application_date DESC, application_id DESC"
    return [_prepare_application(r) for r in query_all(sql, params)]


def get_application(application_id):
    row = query_one(
        "SELECT * FROM application_overview WHERE application_id = %s", (application_id,)
    )
    return _prepare_application(row)


def create_application(data):
    return execute(
        """INSERT INTO applications (job_id, application_date, status, resume_version,
                                     cover_letter_sent, interview_data)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["job_id"], data["application_date"], data["status"], data["resume_version"],
         data["cover_letter_sent"], json.dumps(data["interview_data"])),
    )


def update_application(application_id, data):
    execute(
        """UPDATE applications
           SET job_id = %s, application_date = %s, status = %s, resume_version = %s,
               cover_letter_sent = %s, interview_data = %s
           WHERE application_id = %s""",
        (data["job_id"], data["application_date"], data["status"], data["resume_version"],
         data["cover_letter_sent"], json.dumps(data["interview_data"]), application_id),
    )


def delete_application(application_id):
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))


# ---------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------
def get_all_contacts(search=None, company_id=None):
    sql = """
        SELECT ct.*, c.company_name
        FROM contacts ct JOIN companies c ON ct.company_id = c.company_id
        WHERE 1 = 1
    """
    params = []
    if search:
        sql += " AND (ct.contact_name LIKE %s OR ct.title LIKE %s OR c.company_name LIKE %s)"
        params += [_like(search)] * 3
    if company_id:
        sql += " AND ct.company_id = %s"
        params.append(company_id)
    sql += " ORDER BY ct.contact_name"
    return query_all(sql, params)


def get_contact(contact_id):
    return query_one(
        """SELECT ct.*, c.company_name
           FROM contacts ct JOIN companies c ON ct.company_id = c.company_id
           WHERE ct.contact_id = %s""",
        (contact_id,),
    )


def create_contact(data):
    return execute(
        """INSERT INTO contacts (company_id, contact_name, title, email, phone,
                                 linkedin_url, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (data["company_id"], data["contact_name"], data["title"], data["email"],
         data["phone"], data["linkedin_url"], data["notes"]),
    )


def update_contact(contact_id, data):
    execute(
        """UPDATE contacts
           SET company_id = %s, contact_name = %s, title = %s, email = %s,
               phone = %s, linkedin_url = %s, notes = %s
           WHERE contact_id = %s""",
        (data["company_id"], data["contact_name"], data["title"], data["email"],
         data["phone"], data["linkedin_url"], data["notes"], contact_id),
    )


def delete_contact(contact_id):
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------
def get_dashboard_stats():
    counts = query_one(
        """SELECT
             (SELECT COUNT(*) FROM companies)    AS companies,
             (SELECT COUNT(*) FROM jobs)         AS jobs,
             (SELECT COUNT(*) FROM applications) AS applications,
             (SELECT COUNT(*) FROM contacts)     AS contacts"""
    )

    status_rows = query_all(
        "SELECT status, COUNT(*) AS total FROM applications GROUP BY status"
    )
    by_status = {s: 0 for s in STATUSES}
    for row in status_rows:
        if row["status"] in by_status:
            by_status[row["status"]] = row["total"]

    total = counts["applications"]
    responded = by_status["Screening"] + by_status["Interview"] + by_status["Offer"]
    active = by_status["Applied"] + by_status["Screening"] + by_status["Interview"]

    recent = get_all_applications()[:5]

    # Upcoming interviews come from the interview_data JSON column
    today = date.today().isoformat()
    upcoming = []
    for app in get_all_applications():
        for rnd in app["interview_data"]:
            if rnd.get("date") and rnd["date"] >= today:
                upcoming.append({**rnd, "application_id": app["application_id"],
                                 "job_title": app["job_title"],
                                 "company_name": app["company_name"]})
    upcoming.sort(key=lambda r: r["date"])

    # Most requested skills across all job postings
    skill_counts = {}
    for row in query_all("SELECT requirements FROM jobs"):
        for skill in parse_json(row["requirements"]):
            key = skill.strip().lower()
            name, n = skill_counts.get(key, (skill.strip(), 0))
            skill_counts[key] = (name, n + 1)
    top_skills = sorted(skill_counts.values(), key=lambda x: (-x[1], x[0].lower()))[:8]

    return {
        "counts": counts,
        "by_status": by_status,
        "response_rate": round(responded / total * 100) if total else 0,
        "active": active,
        "offers": by_status["Offer"],
        "recent": recent,
        "upcoming": upcoming[:5],
        "top_skills": top_skills,
    }


# ---------------------------------------------------------------------
# Job Match
# ---------------------------------------------------------------------
def get_jobs_for_matching():
    """All jobs with requirements, company name, and whether the user applied."""
    rows = query_all(
        """SELECT j.job_id, j.job_title, j.job_type, j.salary_min, j.salary_max,
                  j.requirements, c.company_name, c.company_id,
                  (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id)
                      AS application_count
           FROM jobs j
           JOIN companies c ON j.company_id = c.company_id"""
    )
    return [_prepare_job(r) for r in rows]
