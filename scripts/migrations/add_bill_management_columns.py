"""Ensure bill management columns and indexes exist in bills table.

Run:
    python scripts/migrations/add_bill_management_columns.py
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


def ensure_index(cursor, table_name, index_name, index_sql):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table_name, index_name),
    )
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(index_sql)
        print(f"[MIGRATION] Added index {index_name}")


def run_migration():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bill_number VARCHAR(50) NOT NULL UNIQUE,
            order_id INT,
            hotel_id INT,
            table_id INT NOT NULL,
            session_id VARCHAR(100),
            guest_name VARCHAR(255),
            table_number VARCHAR(50),
            items JSON NOT NULL,
            subtotal DECIMAL(10,2) NOT NULL,
            tax_amount DECIMAL(10,2) DEFAULT 0.00,
            cgst_amount DECIMAL(10,2) DEFAULT 0.00,
            sgst_amount DECIMAL(10,2) DEFAULT 0.00,
            charges DECIMAL(10,2) DEFAULT 0.00,
            convenience_fee DECIMAL(10,2) DEFAULT 0.00,
            total_amount DECIMAL(10,2) NOT NULL,
            grand_total DECIMAL(10,2) DEFAULT NULL,
            payment_method VARCHAR(50),
            payment_status ENUM('PENDING', 'PAID') DEFAULT 'PENDING',
            bill_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    ensure_column(cursor, "bills", "order_id", "order_id INT")
    ensure_column(cursor, "bills", "table_number", "table_number VARCHAR(50)")
    ensure_column(cursor, "bills", "guest_name", "guest_name VARCHAR(255)")
    ensure_column(cursor, "bills", "cgst_amount", "cgst_amount DECIMAL(10,2) DEFAULT 0.00")
    ensure_column(cursor, "bills", "sgst_amount", "sgst_amount DECIMAL(10,2) DEFAULT 0.00")
    ensure_column(cursor, "bills", "convenience_fee", "convenience_fee DECIMAL(10,2) DEFAULT 0.00")
    ensure_column(cursor, "bills", "bill_date", "bill_date DATETIME DEFAULT CURRENT_TIMESTAMP")

    ensure_index(cursor, "bills", "idx_bills_hotel_id", "CREATE INDEX idx_bills_hotel_id ON bills (hotel_id)")
    ensure_index(cursor, "bills", "idx_bills_bill_date", "CREATE INDEX idx_bills_bill_date ON bills (bill_date)")
    ensure_index(cursor, "bills", "idx_bills_payment_method", "CREATE INDEX idx_bills_payment_method ON bills (payment_method)")
    ensure_index(cursor, "bills", "idx_bills_payment_status", "CREATE INDEX idx_bills_payment_status ON bills (payment_status)")
    ensure_index(cursor, "bills", "idx_bills_table_number", "CREATE INDEX idx_bills_table_number ON bills (table_number)")

    connection.commit()
    cursor.close()
    connection.close()

    print("[MIGRATION] Bill management schema migration completed")


if __name__ == "__main__":
    run_migration()
