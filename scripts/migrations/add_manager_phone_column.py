"""
Migration: Add phone column to managers table, make email nullable.
Run once: python scripts/migrations/add_manager_phone_column.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database.db import get_db_connection

def run():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Add phone column if not exists
    cursor.execute("SHOW COLUMNS FROM managers LIKE 'phone'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE managers ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT '' AFTER name")
        print("✅ Added 'phone' column to managers table.")
    else:
        print("ℹ️  'phone' column already exists.")

    # Make email nullable
    cursor.execute("ALTER TABLE managers MODIFY COLUMN email VARCHAR(255) NULL DEFAULT NULL")
    print("✅ Made 'email' column nullable.")

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    run()
