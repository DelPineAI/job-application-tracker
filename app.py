"""
app.py - Flask application for the Job Application Tracker.

Routes are grouped by page: Dashboard, Companies, Jobs, Applications,
Contacts, and Job Match. Each table supports full CRUD:
    list (Read)  ->  /<table>
    detail       ->  /<table>/<id>
    create       ->  /<table>/new
    update       ->  /<table>/<id>/edit
    delete       ->  /<table>/<id>/delete   (GET = confirmation page, POST = delete)
"""

import os
import re
from datetime import date, datetime

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database as db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

INTERVIEW_TYPES = ["Phone", "Video", "Technical", "Behavioral", "Panel", "Onsite", "Other"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*\.[^\s]+$", re.IGNORECASE)
PHONE_RE = re.compile(r"^[0-9+()\-.\s xext]{7,20}$", re.IGNORECASE)


# =====================================================================
# Template helpers
# =====================================================================
@app.context_processor
def inject_globals():
    return {
        "STATUSES": db.STATUSES,
        "JOB_TYPES": db.JOB_TYPES,
        "INTERVIEW_TYPES": INTERVIEW_TYPES,
        "today": date.today().isoformat(),
    }


@app.template_filter("money")
def money_filter(value):
    return f"${value:,.0f}" if value is not None else ""


@app.template_filter("salary")
def salary_filter(job):
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo is not None and hi is not None:
        return f"{money_filter(lo)} – {money_filter(hi)}"
    if lo is not None:
        return f"From {money_filter(lo)}"
    if hi is not None:
        return f"Up to {money_filter(hi)}"
    return "Not listed"


@app.template_filter("options")
def options_filter(items, value_key=None, text_key=None):
    """Turn rows (or plain strings) into (value, text) pairs for <select> menus."""
    if value_key is None:
        return [(item, item) for item in items]
    return [(item[value_key], item[text_key]) for item in items]


@app.template_filter("nicedate")
def nicedate_filter(value):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value
    return value.strftime("%b %d, %Y").replace(" 0", " ")


# =====================================================================
# Validation helpers
# =====================================================================
def clean(form, name):
    """Return a stripped string, or None if the field is blank."""
    value = (form.get(name) or "").strip()
    return value or None


def check_length(value, name, label, max_len, errors):
    if value and len(value) > max_len:
        errors[name] = f"{label} must be {max_len} characters or fewer."


def parse_int(form, name, label, errors):
    value = clean(form, name)
    if value is None:
        return None
    value = value.replace(",", "").replace("$", "")
    if not value.isdigit():
        errors[name] = f"{label} must be a whole, non-negative number."
        return None
    number = int(value)
    if number > 2_000_000_000:
        errors[name] = f"{label} is too large."
        return None
    return number


def parse_date(form, name, label, errors, required=False):
    value = clean(form, name)
    if value is None:
        if required:
            errors[name] = f"{label} is required."
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors[name] = f"{label} must be a valid date."
        return None


def check_url(value, name, label, errors):
    if value and not URL_RE.match(value):
        errors[name] = f"{label} must be a full URL starting with http:// or https://"


def parse_skills(text):
    """'Python, SQL , python' -> ['Python', 'SQL'] (trimmed, de-duplicated)."""
    skills, seen = [], set()
    for part in re.split(r"[,\n]", text or ""):
        skill = " ".join(part.split())
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def get_company_id(form, errors):
    value = clean(form, "company_id")
    if not value or not value.isdigit() or not db.get_company(int(value)):
        errors["company_id"] = "Please choose a company."
        return None
    return int(value)


def validate_company(form, company_id=None):
    errors = {}
    data = {f: clean(form, f) for f in
            ("company_name", "industry", "website", "city", "state", "notes")}
    if not data["company_name"]:
        errors["company_name"] = "Company name is required."
    elif db.company_name_exists(data["company_name"], exclude_id=company_id):
        errors["company_name"] = "A company with this name already exists."
    check_length(data["company_name"], "company_name", "Company name", 100, errors)
    check_length(data["industry"], "industry", "Industry", 50, errors)
    check_length(data["website"], "website", "Website", 200, errors)
    check_length(data["city"], "city", "City", 50, errors)
    check_length(data["state"], "state", "State", 50, errors)
    check_url(data["website"], "website", "Website", errors)
    return data, errors


def validate_job(form):
    errors = {}
    data = {
        "company_id": get_company_id(form, errors),
        "job_title": clean(form, "job_title"),
        "job_type": clean(form, "job_type") or "Full-time",
        "salary_min": parse_int(form, "salary_min", "Minimum salary", errors),
        "salary_max": parse_int(form, "salary_max", "Maximum salary", errors),
        "job_url": clean(form, "job_url"),
        "date_posted": parse_date(form, "date_posted", "Date posted", errors),
        "requirements": parse_skills(form.get("requirements")),
    }
    if not data["job_title"]:
        errors["job_title"] = "Job title is required."
    check_length(data["job_title"], "job_title", "Job title", 100, errors)
    if data["job_type"] not in db.JOB_TYPES:
        errors["job_type"] = "Please choose a valid job type."
    if (data["salary_min"] is not None and data["salary_max"] is not None
            and data["salary_min"] > data["salary_max"]):
        errors["salary_max"] = "Maximum salary must be greater than or equal to the minimum."
    check_length(data["job_url"], "job_url", "Job URL", 300, errors)
    check_url(data["job_url"], "job_url", "Job URL", errors)
    if data["date_posted"] and data["date_posted"] > date.today():
        errors["date_posted"] = "Date posted can't be in the future."
    if any(len(s) > 50 for s in data["requirements"]):
        errors["requirements"] = "Each skill must be 50 characters or fewer."
    return data, errors


def read_interview_rounds(form, errors):
    """Collect the repeating interview-round rows into a list of dicts (JSON column)."""
    dates = form.getlist("interview_date")
    types = form.getlist("interview_type")
    people = form.getlist("interviewer")
    notes = form.getlist("interview_notes")
    rounds = []
    for i in range(len(dates)):
        row = {
            "date": (dates[i] if i < len(dates) else "").strip(),
            "type": (types[i] if i < len(types) else "").strip(),
            "interviewer": (people[i] if i < len(people) else "").strip(),
            "notes": (notes[i] if i < len(notes) else "").strip(),
        }
        if not (row["date"] or row["interviewer"] or row["notes"]):
            continue  # skip completely empty rows
        if not row["date"]:
            errors["interview_data"] = "Every interview round needs a date."
        else:
            try:
                datetime.strptime(row["date"], "%Y-%m-%d")
            except ValueError:
                errors["interview_data"] = "Interview dates must be valid dates."
        if row["type"] not in INTERVIEW_TYPES:
            row["type"] = "Other"
        rounds.append(row)
    rounds.sort(key=lambda r: r["date"])
    return rounds


def validate_application(form):
    errors = {}
    job_id = clean(form, "job_id")
    if not job_id or not job_id.isdigit() or not db.get_job(int(job_id)):
        errors["job_id"] = "Please choose a job."
        job_id = None
    data = {
        "job_id": int(job_id) if job_id else None,
        "application_date": parse_date(form, "application_date", "Application date",
                                       errors, required=True),
        "status": clean(form, "status") or "Applied",
        "resume_version": clean(form, "resume_version"),
        "cover_letter_sent": form.get("cover_letter_sent") == "on",
        "interview_data": read_interview_rounds(form, errors),
    }
    if data["status"] not in db.STATUSES:
        errors["status"] = "Please choose a valid status."
    check_length(data["resume_version"], "resume_version", "Resume version", 50, errors)
    if data["application_date"] and data["application_date"] > date.today():
        errors["application_date"] = "Application date can't be in the future."
    return data, errors


def validate_contact(form):
    errors = {}
    data = {
        "company_id": get_company_id(form, errors),
        "contact_name": clean(form, "contact_name"),
        "title": clean(form, "title"),
        "email": clean(form, "email"),
        "phone": clean(form, "phone"),
        "linkedin_url": clean(form, "linkedin_url"),
        "notes": clean(form, "notes"),
    }
    if not data["contact_name"]:
        errors["contact_name"] = "Contact name is required."
    check_length(data["contact_name"], "contact_name", "Name", 100, errors)
    check_length(data["title"], "title", "Title", 100, errors)
    check_length(data["email"], "email", "Email", 100, errors)
    check_length(data["linkedin_url"], "linkedin_url", "LinkedIn URL", 200, errors)
    if data["email"] and not EMAIL_RE.match(data["email"]):
        errors["email"] = "Please enter a valid email address."
    if data["phone"] and not PHONE_RE.match(data["phone"]):
        errors["phone"] = "Please enter a valid phone number (max 20 characters)."
    check_url(data["linkedin_url"], "linkedin_url", "LinkedIn URL", errors)
    return data, errors


def form_errors(_errors):
    flash("Please fix the highlighted fields and try again.", "error")


def plural(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


def get_or_404(record):
    if record is None:
        abort(404)
    return record


# =====================================================================
# Dashboard
# =====================================================================
@app.route("/")
def dashboard():
    return render_template("dashboard.html", stats=db.get_dashboard_stats())


# =====================================================================
# Companies
# =====================================================================
@app.route("/companies")
def companies():
    q = request.args.get("q", "").strip()
    return render_template("companies.html", companies=db.get_all_companies(q), q=q)


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    if request.method == "POST":
        data, errors = validate_company(request.form)
        if not errors:
            new_id = db.create_company(data)
            flash(f"Company “{data['company_name']}” added.", "success")
            return redirect(url_for("company_detail", company_id=new_id))
        form_errors(errors)
        return render_template("company_form.html", form=request.form, errors=errors,
                               mode="new")
    return render_template("company_form.html", form={}, errors={}, mode="new")


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404(db.get_company(company_id))
    return render_template(
        "company_detail.html",
        company=company,
        jobs=db.get_jobs_for_company(company_id),
        contacts=db.get_all_contacts(company_id=company_id),
        applications=db.get_all_applications(company_id=company_id),
    )


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_or_404(db.get_company(company_id))
    if request.method == "POST":
        data, errors = validate_company(request.form, company_id=company_id)
        if not errors:
            db.update_company(company_id, data)
            flash(f"Company “{data['company_name']}” updated.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        form_errors(errors)
        return render_template("company_form.html", form=request.form, errors=errors,
                               mode="edit", record=company)
    return render_template("company_form.html", form=company, errors={}, mode="edit",
                           record=company)


@app.route("/companies/<int:company_id>/delete", methods=["GET", "POST"])
def company_delete(company_id):
    company = get_or_404(db.get_company(company_id))
    if request.method == "POST":
        db.delete_company(company_id)
        flash(f"Company “{company['company_name']}” deleted.", "success")
        return redirect(url_for("companies"))
    impact = db.get_company_delete_impact(company_id)
    cascade = [plural(impact[k], k[:-1]) for k in ("jobs", "applications", "contacts")
               if impact[k]]
    return render_template(
        "confirm_delete.html",
        kind="company", name=company["company_name"], cascade=cascade,
        action=url_for("company_delete", company_id=company_id),
        cancel=url_for("company_detail", company_id=company_id),
    )


# =====================================================================
# Jobs
# =====================================================================
def job_form_defaults(job=None):
    if job is None:
        return {"job_type": "Full-time", "company_id": request.args.get("company_id", "")}
    form = dict(job)
    form["requirements"] = ", ".join(job["requirements"])
    return form


@app.route("/jobs")
def jobs():
    q = request.args.get("q", "").strip()
    job_type = request.args.get("type", "")
    company_id = request.args.get("company_id", type=int)
    return render_template(
        "jobs.html",
        jobs=db.get_all_jobs(q, job_type if job_type in db.JOB_TYPES else None, company_id),
        companies=db.get_company_choices(),
        q=q, job_type=job_type, company_id=company_id,
    )


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    companies_list = db.get_company_choices()
    if request.method == "POST":
        data, errors = validate_job(request.form)
        if not errors:
            new_id = db.create_job(data)
            flash(f"Job “{data['job_title']}” added.", "success")
            return redirect(url_for("job_detail", job_id=new_id))
        form_errors(errors)
        return render_template("job_form.html", form=request.form, errors=errors,
                               companies=companies_list, mode="new")
    return render_template("job_form.html", form=job_form_defaults(), errors={},
                           companies=companies_list, mode="new")


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_or_404(db.get_job(job_id))
    return render_template("job_detail.html", job=job,
                           applications=db.get_all_applications(job_id=job_id))


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = get_or_404(db.get_job(job_id))
    companies_list = db.get_company_choices()
    if request.method == "POST":
        data, errors = validate_job(request.form)
        if not errors:
            db.update_job(job_id, data)
            flash(f"Job “{data['job_title']}” updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        form_errors(errors)
        return render_template("job_form.html", form=request.form, errors=errors,
                               companies=companies_list, mode="edit", record=job)
    return render_template("job_form.html", form=job_form_defaults(job), errors={},
                           companies=companies_list, mode="edit", record=job)


@app.route("/jobs/<int:job_id>/delete", methods=["GET", "POST"])
def job_delete(job_id):
    job = get_or_404(db.get_job(job_id))
    if request.method == "POST":
        db.delete_job(job_id)
        flash(f"Job “{job['job_title']}” deleted.", "success")
        return redirect(url_for("jobs"))
    impact = db.get_job_delete_impact(job_id)
    cascade = [plural(impact["applications"], "application")] if impact["applications"] else []
    return render_template(
        "confirm_delete.html",
        kind="job", name=f"{job['job_title']} at {job['company_name']}", cascade=cascade,
        action=url_for("job_delete", job_id=job_id),
        cancel=url_for("job_detail", job_id=job_id),
    )


# =====================================================================
# Applications
# =====================================================================
def application_form_context(form, errors, mode, record=None, rounds=None):
    return render_template(
        "application_form.html", form=form, errors=errors, mode=mode, record=record,
        jobs=db.get_job_choices(), rounds=rounds or [],
    )


@app.route("/applications")
def applications():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    return render_template(
        "applications.html",
        applications=db.get_all_applications(status if status in db.STATUSES else None, q),
        status=status, q=q,
    )


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    if request.method == "POST":
        data, errors = validate_application(request.form)
        if not errors:
            new_id = db.create_application(data)
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
        form_errors(errors)
        return application_form_context(request.form, errors, "new",
                                        rounds=data["interview_data"])
    defaults = {"application_date": date.today().isoformat(), "status": "Applied",
                "job_id": request.args.get("job_id", "")}
    return application_form_context(defaults, {}, "new")


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = get_or_404(db.get_application(application_id))
    return render_template("application_detail.html", app_row=application)


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    application = get_or_404(db.get_application(application_id))
    if request.method == "POST":
        data, errors = validate_application(request.form)
        if not errors:
            db.update_application(application_id, data)
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        form_errors(errors)
        return application_form_context(request.form, errors, "edit", application,
                                        rounds=data["interview_data"])
    form = dict(application)
    form["application_date"] = application["application_date"].isoformat()
    return application_form_context(form, {}, "edit", application,
                                    rounds=application["interview_data"])


@app.route("/applications/<int:application_id>/delete", methods=["GET", "POST"])
def application_delete(application_id):
    application = get_or_404(db.get_application(application_id))
    if request.method == "POST":
        db.delete_application(application_id)
        flash("Application deleted.", "success")
        return redirect(url_for("applications"))
    return render_template(
        "confirm_delete.html",
        kind="application",
        name=f"{application['job_title']} at {application['company_name']} "
             f"(applied {nicedate_filter(application['application_date'])})",
        cascade=[],
        action=url_for("application_delete", application_id=application_id),
        cancel=url_for("application_detail", application_id=application_id),
    )


# =====================================================================
# Contacts
# =====================================================================
@app.route("/contacts")
def contacts():
    q = request.args.get("q", "").strip()
    return render_template("contacts.html", contacts=db.get_all_contacts(q), q=q)


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    companies_list = db.get_company_choices()
    if request.method == "POST":
        data, errors = validate_contact(request.form)
        if not errors:
            new_id = db.create_contact(data)
            flash(f"Contact “{data['contact_name']}” added.", "success")
            return redirect(url_for("contact_detail", contact_id=new_id))
        form_errors(errors)
        return render_template("contact_form.html", form=request.form, errors=errors,
                               companies=companies_list, mode="new")
    return render_template("contact_form.html",
                           form={"company_id": request.args.get("company_id", "")},
                           errors={}, companies=companies_list, mode="new")


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    contact = get_or_404(db.get_contact(contact_id))
    return render_template("contact_detail.html", contact=contact)


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = get_or_404(db.get_contact(contact_id))
    companies_list = db.get_company_choices()
    if request.method == "POST":
        data, errors = validate_contact(request.form)
        if not errors:
            db.update_contact(contact_id, data)
            flash(f"Contact “{data['contact_name']}” updated.", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
        form_errors(errors)
        return render_template("contact_form.html", form=request.form, errors=errors,
                               companies=companies_list, mode="edit", record=contact)
    return render_template("contact_form.html", form=contact, errors={},
                           companies=companies_list, mode="edit", record=contact)


@app.route("/contacts/<int:contact_id>/delete", methods=["GET", "POST"])
def contact_delete(contact_id):
    contact = get_or_404(db.get_contact(contact_id))
    if request.method == "POST":
        db.delete_contact(contact_id)
        flash(f"Contact “{contact['contact_name']}” deleted.", "success")
        return redirect(url_for("contacts"))
    return render_template(
        "confirm_delete.html",
        kind="contact", name=f"{contact['contact_name']} ({contact['company_name']})",
        cascade=[],
        action=url_for("contact_delete", contact_id=contact_id),
        cancel=url_for("contact_detail", contact_id=contact_id),
    )


# =====================================================================
# Job Match
# =====================================================================
def normalize_skill(skill):
    """Case- and whitespace-insensitive key: ' power  BI ' -> 'power bi'."""
    return " ".join(skill.lower().split())


def calculate_match(user_skills, requirements):
    """
    Compare the user's skills with one job's requirements.

    match % = (required skills the user has) / (total required skills) * 100
    e.g. user {Python, SQL, Flask} vs job [Python, SQL, Tableau] -> 2/3 = 67%
    """
    have = {normalize_skill(s) for s in user_skills}
    matched = [r for r in requirements if normalize_skill(r) in have]
    missing = [r for r in requirements if normalize_skill(r) not in have]
    total = len(requirements)
    percent = round(len(matched) / total * 100) if total else 0
    return {"percent": percent, "matched": matched, "missing": missing, "total": total}


def rank_jobs(user_skills, jobs_list, min_percent=1):
    """Score every job, drop those below min_percent, and sort best match first."""
    results = []
    for job in jobs_list:
        if not job["requirements"]:
            continue  # can't score a job that lists no requirements
        match = calculate_match(user_skills, job["requirements"])
        if match["percent"] >= min_percent:
            results.append({**job, **match})
    results.sort(key=lambda r: (-r["percent"], -len(r["matched"]), r["job_title"].lower()))
    return results


@app.route("/job-match")
def job_match():
    skills_text = request.args.get("skills", "")
    min_percent = request.args.get("min", 1, type=int)
    user_skills = parse_skills(skills_text)
    all_jobs = db.get_jobs_for_matching()
    results = rank_jobs(user_skills, all_jobs, min_percent) if user_skills else []
    return render_template(
        "job_match.html",
        skills_text=", ".join(user_skills) if user_skills else skills_text,
        user_skills=user_skills,
        results=results,
        min_percent=min_percent,
        all_skills=db.get_all_skills(),
        scored_jobs=sum(1 for j in all_jobs if j["requirements"]),
    )


# =====================================================================
# Errors
# =====================================================================
@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", title="Page not found",
                           message="That record doesn't exist or was deleted."), 404


@app.errorhandler(mysql.connector.Error)
def database_error(error):
    app.logger.exception("Database error")
    return render_template(
        "error.html", title="Database error",
        message="The app couldn't talk to MySQL. Make sure MySQL is running, "
                "you ran `python init_db.py`, and your .env settings are correct.",
        detail=str(error),
    ), 500


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
