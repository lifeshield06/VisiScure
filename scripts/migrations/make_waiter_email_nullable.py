"""
Migration: Make waiters.email column nullable (email is now optional).
Run once: python scripts/migrations/make_waiter_email_nullable.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database.db import get_db_connection

def run():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE waiters MODIFY COLUMN email VARCHAR(255) NULL DEFAULT NULL")
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ waiters.email is now nullable.")

if __name__ == "__main__":
    run()
