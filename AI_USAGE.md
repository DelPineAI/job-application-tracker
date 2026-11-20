# AI Usage Documentation

## Tools Used

- **Claude (Anthropic, Claude Opus 5.5 in the Claude app)**: the main tool. I used it across many separate conversations, not one. We scoped the project, chose the framework and architecture, decided on features, planned secure scaffolding, worked on design, and iterated through many rounds of testing and refinement. I made the decisions and steered each round. Claude acted as a pair programmer and sounding board.
- Claude was also used to help write the setup instructions and plan the demo video narration.

## Key Prompts

There was no single prompt. The work happened through a lot of back-and-forth over many conversations. These are representative examples of the kinds of prompts I used at each stage:

**Scoping**
- "Here's the project spec. Before we write any code, help me scope it out: what's required, what's optional, and what we should leave out."
- "Break this spec down requirement by requirement so I can see exactly what the project needs."

**Architecture**
- "What's the best framework and architecture for this project, given the requirements? Compare the options and their trade-offs."
- "How should I structure the database layer and the routes so the code stays clean and easy to maintain?"

**Features**
- "What features would make this app genuinely useful beyond the minimum requirements?"
- "How should the Job Match percentage be calculated so it's accurate and easy to explain?"
- "What should the user see before deleting a company that has jobs and applications attached to it?"

**Security and scaffolding**
- "What's the most secure way to set up the scaffolding: database connections, queries, and form validation?"
- "Make sure every query is protected against SQL injection, and explain how."

**Design**
- "Let's make the design consistent across every page. How should the layout and forms be organized?"

**Testing and refinement**
- "I tested the app and found that [issue]. Why is this happening, and what's the cleanest fix?"
- "Walk me through how the cascading deletes and the match calculation work so I can explain them."

The specification's own suggested prompts were also used:
- "Write a Flask route to display all jobs with company names using JOIN."
- "Create a function to calculate skill match percentage."

## What AI Generated (What Worked Well)

After the scope, architecture, and features were settled, Claude generated the code to match those decisions:

- **`schema.sql`**: the four required tables with foreign keys, two JSON columns (`requirements`, `interview_data`), ENUMs, CHECK constraints on salaries, a UNIQUE company name, a view (`application_overview`), indexes, and sample data with dates relative to `CURDATE()` so the demo always looks current.
- **`database.py`**: one function per operation, all using parameterized queries (`%s`) to prevent SQL injection, plus a `db_cursor()` context manager that commits or rolls back and always closes the connection.
- **`app.py`**: CRUD routes for all four tables, server-side validation with per-field error messages, delete confirmation pages that show what will cascade, dashboard statistics, and the Job Match algorithm.
- **Templates/CSS**: a consistent layout with shared Jinja macros for form fields, so every form looks and behaves the same, and an editable list of interview rounds saved as JSON.
- **`init_db.py`**: creates the database with `python init_db.py`, so the MySQL command-line client isn't required.

What worked well was working in stages. Settling scope and architecture first meant the generated code fit a plan instead of being a guess, and the security patterns were built in from the start.

## Problems Found During Testing and How They Were Fixed

I tested every page, every create/update/delete, validation, and the Job Match results across many rounds. Testing found real issues, which were fixed in later iterations:

- **`ONLY_FULL_GROUP_BY` failures.** List pages that used `SELECT c.*, COUNT(...) ... GROUP BY c.company_id` could fail under MySQL's strict mode. *Fix:* rewritten with correlated subqueries and re-tested with strict SQL mode on.
- **A Jinja filter that doesn't exist.** The job form used a `zip` filter, which Jinja doesn't have. *Fix:* a small custom `options` template filter.
- **Wrong menu item highlighted.** The sidebar highlighted "Jobs" on the Job Match page because both routes start with `job`. *Fix:* the highlighting logic now maps each page to its section explicitly.
- **Grammar in delete warnings.** The cascade warning said "1 jobs." *Fix:* a `plural()` helper.
- **Duplicate skills.** Entering "Python, python" stored both. *Fix:* skill parsing now trims spaces and removes case-insensitive duplicates.

## My Review and Modifications

- **Scope:** I worked through the specification with Claude to decide what was required, what was optional, and what features to add.
- **Architecture:** I weighed framework and structure options before settling on Flask, MySQL, Jinja templates, and a separate database module.
- **Features and design:** I decided how features should behave and what the app should look like, and pushed for revisions when something wasn't right.
- **Security:** I made sure the foundation was built securely from the start: parameterized queries, transaction handling, server-side validation, and database constraints.
- **Testing:** I tested the app end to end, repeatedly, and brought each issue back into the conversation to fix.
- **Understanding:** I reviewed the code to understand how it works, especially the match calculation and cascading deletes, so I can explain and defend it.

## Lessons Learned

- **Planning with AI matters as much as coding with it.** Spending time on scope, architecture, and features first made the build much smoother.
- **Iteration beats one-shot generation.** The best results came from many rounds of back-and-forth, not from a single prompt.
- **Always test AI-generated code.** Several bugs only appeared when every page was actually used (an invalid template filter, a navigation bug, a SQL-mode issue).
- **Give the AI full context.** Sharing the complete specification produced a schema that matched the required columns exactly.
- **Ask for explanations, not just code.** Understanding the code is what makes it possible to own it.
- **AI handles boilerplate fast** (CRUD routes, forms, CSS), which leaves more time for judgment calls: scope, security, data validation, and testing.
- **Be transparent.** Documenting how AI was used, and what I decided and verified, is part of using it responsibly.