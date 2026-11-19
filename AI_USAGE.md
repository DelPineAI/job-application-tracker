# AI Usage Documentation

## Tools Used
- **Claude (Anthropic, Claude Opus 5.5 in the Claude app)** — the main tool. It read the project specification, generated the database schema, Flask app, templates, CSS, and documentation, and tested the app end to end (every page, every create/update/delete, validation, and the Job Match results) before handing it over.
- **Claude** was also used to write the setup instructions and to plan the demo video narration.

## Key Prompts
1. *"Please help me complete this project [Job Application Tracker spec attached]. Only have me do what is needed… prepare the whole project and then guide me on how to do the narration."* — the main prompt; Claude produced the full project from the specification document.
2. The spec's own suggestions, which shaped what Claude built:
   - "Write a Flask route to display all jobs with company names using JOIN."
   - "Create a function to calculate skill match percentage."

## What AI Generated (What Worked Well)
- **schema.sql**: the 4 required tables with foreign keys, the two JSON columns (`requirements`, `interview_data`), ENUMs, CHECK constraints for salaries, a `UNIQUE` company name, a view (`application_overview`), indexes, and sample data whose dates are relative to `CURDATE()` so the demo always looks current.
- **database.py**: one function per operation, all using parameterized queries (`%s`) to prevent SQL injection, plus a `db_cursor()` context manager that commits or rolls back and always closes the connection.
- **app.py**: CRUD routes for all four tables, server-side validation with per-field error messages, delete confirmation pages that show what will cascade, the dashboard statistics, and the Job Match algorithm.
- **Templates/CSS**: a consistent layout with shared Jinja macros for form fields, so every form looks and behaves the same; an editable list of interview rounds that is saved as JSON.
- **init_db.py**: lets the database be created with `python init_db.py`, so the mysql command-line client isn't required.

## Problems Found During Testing and How They Were Fixed
Testing the AI's first version found real issues, which were then fixed:
- **`GROUP BY` queries could fail on MySQL's `ONLY_FULL_GROUP_BY` mode.** The list pages originally used `SELECT c.*, COUNT(...) ... GROUP BY c.company_id`. They were rewritten to use correlated subqueries, and the app was re-tested with strict SQL mode turned on.
- **A Jinja filter that doesn't exist.** The job form used a `zip` filter to build dropdown options, which Jinja doesn't have. A small custom `options` template filter was added instead.
- **Wrong menu item highlighted.** The sidebar highlighted "Jobs" while on the Job Match page because both routes start with `job`. The highlighting logic was rewritten to map each page to its section explicitly.
- **Grammar in delete warnings.** The cascade warning said "1 jobs"; a `plural()` helper fixed it.
- **Duplicate skills.** Entering "Python, python" stored both. Skill parsing now trims spaces and removes case-insensitive duplicates.

## My Review and Modifications
<!-- Edward: replace this with 2–4 honest bullets about what YOU checked or changed, e.g.
- Ran the app locally on my machine and walked through every page before recording.
- Changed the sample data to ...
- Asked Claude to explain ... until I understood it. -->

## Lessons Learned
- **Always test AI-generated code.** The first version looked complete but still had bugs that only showed up when every page was actually run (an invalid template filter, a navigation bug, a SQL-mode issue).
- **Give the AI the full specification.** Uploading the spec document produced a schema that matched the required columns exactly, instead of a guess.
- **Ask for explanations, not just code.** Understanding how the match percentage and the cascading deletes work is what makes it possible to explain and defend the code in the demo.
- **AI is fast at boilerplate** (CRUD routes, forms, CSS), which leaves more time for the parts that need judgment: data validation, database constraints, and testing.
- **Be transparent.** Documenting what the AI produced and what was checked or changed is part of using it responsibly.
