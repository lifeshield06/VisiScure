"""Add discount fields to bills table.

Run:
    python scripts/migrations/add_bill_discount_columns.py
"""

from database.db import get_db_connection


def ensure_column(cursor, table_name, column_name, column_definition):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
        print(f"[MIGRATION] Added column {table_name}.{column_name}")


def run_migration():
    connection = get_db_connection()
    cursor = connection.cursor()

    ensure_column(cursor, "bills", "discount_percent", "discount_percent DECIMAL(5,2) DEFAULT 0.00")
    ensure_column(cursor, "bills", "discount_amount", "discount_amount DECIMAL(10,2) DEFAULT 0.00")
    ensure_column(cursor, "bills", "final_total", "final_total DECIMAL(10,2) DEFAULT NULL")

    connection.commit()
    cursor.close()
    connection.close()

    print("[MIGRATION] Bill discount columns migration completed")


if __name__ == "__main__":
    run_migration()
