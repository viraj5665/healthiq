"""
Apply all SQL migrations in order. Idempotent — safe to re-run.
Used by Render's startCommand before uvicorn boots.
"""

import os
import sys
import glob

import psycopg2

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)

# Railway sometimes gives a postgres:// URL; psycopg2 needs postgresql://
DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

migration_dir = os.path.join(os.path.dirname(__file__), "..", "infra", "migrations")
all_sql = glob.glob(os.path.join(migration_dir, "*.sql"))

# init.sql must run first (enables uuid-ossp extension + base schema);
# then numbered files in ascending order
init   = [f for f in all_sql if os.path.basename(f) == "init.sql"]
others = sorted(f for f in all_sql if os.path.basename(f) != "init.sql")
files  = init + others

for path in files:
    name = os.path.basename(path)
    try:
        with open(path) as fh:
            sql = fh.read()
        cur.execute(sql)
        print(f"  ✓ {name}")
    except Exception as exc:
        print(f"  ✗ {name}: {exc}", file=sys.stderr)

cur.close()
conn.close()
print("Migrations complete.")
