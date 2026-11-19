# Job Application Tracker

A full-stack web app for tracking a job search: companies, job postings, applications (with interview rounds), and contacts. It also has a **Job Match** feature that ranks jobs by how many of their required skills you have.

**Stack:** MySQL · Python 3 / Flask · HTML / CSS (no frameworks, no CDN — works offline)

🎥 **Demo video:** `demo_video.mp4` (or `demo_video.mov`) in the root of this repository — a 3–7 minute walkthrough of the client, server and database.

---

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Totals, response rate, offers, applications by status, upcoming interviews (read from JSON), most requested skills, recent applications |
| **Companies** | List + search, detail page (with that company's jobs, contacts, applications), add, edit, delete with confirmation |
| **Jobs** | List + search + filter by type/company, detail, add, edit, delete. Required skills are stored as a JSON array |
| **Applications** | List + filter by status + search, detail with interview timeline, add, edit, delete. Interview rounds are stored in a JSON column |
| **Contacts** | List + search, detail, add, edit, delete |
| **Job Match** | Enter your skills → jobs ranked by match % with matched and missing skills |

**Validation:** required fields, max lengths, valid URLs/emails/phones, valid dates (not in the future), salary min ≤ max, duplicate company names, valid dropdown values, and foreign keys that must exist. Errors are shown next to each field and the form keeps what you typed.

**Deletes** always go through a confirmation page that warns what else will be removed (for example, deleting a company also deletes its jobs, applications, and contacts via `ON DELETE CASCADE`).

---

## Setup

### 1. Requirements
- Python 3.9 or newer
- MySQL 8.0 or newer (running locally)

### 2. Get the code and install packages
```bash
git clone <this-repo-url>
cd job_tracker
python -m venv venv                 # optional but recommended
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure your MySQL login
Copy the example settings file and put your MySQL password in it:
```bash
cp .env.example .env                # Windows: copy .env.example .env
```
Then open `.env` and set `DB_PASSWORD=` to your MySQL root password (leave it blank if your root user has no password).

### 4. Create the database
```bash
python init_db.py
```
This runs `schema.sql`, which creates the `job_tracker` database, the 4 tables, a view, and sample data.
(Alternatively: `mysql -u root -p < schema.sql`.) Running it again resets the data.

### 5. Run the app
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser.

> If port 5000 is busy (common on macOS because of AirPlay Receiver), add `PORT=5001` to `.env` and open http://127.0.0.1:5001.

### Troubleshooting
| Problem | Fix |
|---|---|
| `Access denied for user 'root'` | Wrong `DB_PASSWORD` in `.env` |
| `Can't connect to MySQL server` | MySQL isn't running — start the MySQL service |
| `Unknown database 'job_tracker'` | Run `python init_db.py` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` (inside your venv) |

---

## Database design

```
companies 1 ──< jobs 1 ──< applications
    1
    └──< contacts
```

| Table | Key columns | Notes |
|---|---|---|
| `companies` | `company_id` PK | `company_name` is NOT NULL and UNIQUE |
| `jobs` | `job_id` PK, `company_id` FK → companies | `job_type` ENUM, `requirements` **JSON** array of skills, CHECK salary_min ≤ salary_max |
| `applications` | `application_id` PK, `job_id` FK → jobs | `status` ENUM, `cover_letter_sent` BOOLEAN, `interview_data` **JSON** array of rounds |
| `contacts` | `contact_id` PK, `company_id` FK → companies | |

- All foreign keys use `ON DELETE CASCADE ON UPDATE CASCADE`.
- `application_overview` is a **view** joining applications → jobs → companies; the Applications pages read from it.
- Indexes on `applications.status` and `applications.application_date` support the filters and sorting.
- Sample data uses dates relative to `CURDATE()` so the dashboard always shows realistic "recent" and "upcoming" items.

Example JSON values:
```json
requirements:   ["Python", "SQL", "Flask"]
interview_data: [{"date": "2026-11-21", "type": "Technical", "interviewer": "James Carter", "notes": "Live coding"}]
```

`demo_queries.sql` has ready-made queries for looking at the tables, foreign keys, and JSON columns directly in MySQL.

---

## Job Match algorithm

For each job that lists requirements:

```
match % = (required skills you have) / (total required skills) × 100
```

- Skills are compared case- and whitespace-insensitively (`" python "` = `"Python"`).
- Results are sorted by match %, then by number of matched skills, then title.
- Each result shows the %, the `matched/total` count, the skills you **have**, and the skills you're **missing**.
- A minimum-match filter (Any / 50% / 75% / 100% / all jobs) narrows the list.

Example (matches the project spec):
```
Your Skills: Python, SQL, Flask
1. Software Developer at TechCorp – 100% (3/3 skills)
2. Data Analyst at DataCo – 67% (2/3 skills)   Missing: Tableau
```

The logic lives in `calculate_match()` and `rank_jobs()` in `app.py`.

---

## Project structure

```
job_tracker/
├── app.py              # Flask routes, form validation, Job Match logic
├── database.py         # MySQL connection + all SQL queries (parameterized)
├── init_db.py          # Creates the database by running schema.sql
├── schema.sql          # Tables, foreign keys, JSON columns, view, sample data
├── demo_queries.sql    # Queries to inspect the database during the demo
├── templates/          # Jinja2 HTML templates
│   ├── base.html, _macros.html
│   ├── dashboard.html
│   ├── companies.html, company_form.html, company_detail.html
│   ├── jobs.html, job_form.html, job_detail.html
│   ├── applications.html, application_form.html, application_detail.html
│   ├── contacts.html, contact_form.html, contact_detail.html
│   ├── job_match.html, confirm_delete.html, error.html
├── static/
│   ├── style.css
│   └── app.js          # Small enhancements (add interview rounds, skill chips)
├── AI_USAGE.md         # GenAI documentation
├── requirements.txt
├── .env.example
└── demo_video.mp4 / .mov
```

## How a request flows
1. The browser requests a URL such as `/jobs/3/edit` (**client**).
2. Flask matches it to a route in `app.py` (**server**), which validates any form input.
3. The route calls a function in `database.py`, which runs a parameterized SQL query against MySQL (**database**).
4. The results are passed to a Jinja template, which renders HTML back to the browser.
