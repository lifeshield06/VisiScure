"""
Migration: Add is_active column to menu_dishes table.
Run once: python scripts/migrations/add_dish_is_active_column.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from database.db import get_db_connection

def run():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM menu_dishes LIKE 'is_active'")
    if not cursor.fetchone():
        cursor.execute(
            "ALTER TABLE menu_dishes ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1"
        )
        conn.commit()
        print("✅ Added 'is_active' column to menu_dishes (default 1 = Active).")
    else:
        print("ℹ️  'is_active' column already exists.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run()
