"""
Migration: Create waiter_notifications table for kitchen order-ready alerts.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection


def migrate():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        print('Creating waiter_notifications table...')
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT NOT NULL,
                order_id INT NOT NULL,
                table_id INT NOT NULL,
                waiter_id INT NOT NULL,
                type VARCHAR(50) NOT NULL,
                status ENUM('pending', 'completed') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,

                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES table_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE,
                FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE,

                INDEX idx_waiter_pending (waiter_id, type, status),
                INDEX idx_order_lookup (order_id, table_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        connection.commit()
        cursor.close()
        connection.close()

        print('✓ waiter_notifications table created successfully')
        return True
    except Exception as exc:
        print(f'✗ Error creating waiter_notifications table: {exc}')
        return False


def rollback():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        print('Rolling back waiter_notifications table...')
        cursor.execute('DROP TABLE IF EXISTS waiter_notifications')
        connection.commit()

        cursor.close()
        connection.close()

        print('✓ waiter_notifications table dropped successfully')
        return True
    except Exception as exc:
        print(f'✗ Error rolling back waiter_notifications table: {exc}')
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        print('Running rollback...')
        rollback()
    else:
        print('Running migration...')
        migrate()
