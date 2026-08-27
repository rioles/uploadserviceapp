#!/bin/bash
set -e

echo "Waiting for database to be available..."
python << END
import sys
import time
import psycopg2
import os

max_retries = 30
retry_interval = 2

for i in range(max_retries):
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            host=os.environ.get("DB_HOST"),
            port=os.environ.get("DB_PORT", "5432"),
            connect_timeout=5,
        )
        conn.close()
        print("Database is available.")
        sys.exit(0)
    except psycopg2.OperationalError as e:
        print(f"Database not ready yet ({i + 1}/{max_retries}): {e}")
        time.sleep(retry_interval)

print("Could not connect to the database after several retries.")
sys.exit(1)
END

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"
