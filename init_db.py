"""
init_db.py - Create (or reset) the job_tracker database from schema.sql.

Usage:
    python init_db.py

Uses the same DB_HOST / DB_USER / DB_PASSWORD settings as the app (.env file),
so you don't need the mysql command-line client.
"""

import re
import sys
from pathlib import Path

import mysql.connector

from database import DB_CONFIG


def split_statements(sql_text):
    """Split the script on semicolons that end a line, skipping comment lines."""
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    chunks = re.split(r";\s*$", "\n".join(lines), flags=re.MULTILINE)
    return [c.strip() for c in chunks if c.strip()]


def main():
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    config = {k: v for k, v in DB_CONFIG.items() if k != "database"}

    try:
        conn = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"Could not connect to MySQL: {err}")
        print("Check that MySQL is running and that DB_USER/DB_PASSWORD in .env are correct.")
        sys.exit(1)

    cursor = conn.cursor()
    statements = split_statements(schema)
    for statement in statements:
        cursor.execute(statement)
        if cursor.with_rows:
            cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Database '{DB_CONFIG['database']}' created ({len(statements)} statements run).")


if __name__ == "__main__":
    main()
