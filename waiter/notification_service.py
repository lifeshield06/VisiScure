"""
Waiter notification service for kitchen order-ready alerts.
"""

from database.db import get_db_connection
from mysql.connector import Error


class WaiterNotificationService:
    """Service layer for waiter-facing order notifications."""

    _schema_checked = False

    @staticmethod
    def _ensure_schema(cursor):
        if WaiterNotificationService._schema_checked:
            return

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

        WaiterNotificationService._schema_checked = True

    @staticmethod
    def create_order_ready_notification(order_id, table_id):
        """Create a pending order-ready notification for the waiter assigned to the table."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            WaiterNotificationService._ensure_schema(cursor)

            cursor.execute(
                """
                SELECT
                    t.id,
                    t.hotel_id,
                    t.waiter_id,
                    (
                        SELECT wta.waiter_id
                        FROM waiter_table_assignments wta
                        WHERE wta.table_id = t.id
                        ORDER BY wta.assigned_at ASC, wta.waiter_id ASC
                        LIMIT 1
                    ) AS mapped_waiter_id
                FROM tables t
                WHERE t.id = %s
                LIMIT 1
                """,
                (table_id,)
            )
            table_row = cursor.fetchone()

            if not table_row:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Table not found'}

            waiter_id = table_row.get('waiter_id') or table_row.get('mapped_waiter_id')
            if waiter_id is None:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'No waiter assigned for table'}

            waiter_id = int(waiter_id)

            # Prevent duplicate pending notifications for the same order+waiter.
            cursor.execute(
                """
                SELECT id
                FROM waiter_notifications
                WHERE order_id = %s
                  AND table_id = %s
                  AND waiter_id = %s
                  AND type = 'order_ready'
                  AND status = 'pending'
                LIMIT 1
                """,
                (order_id, table_id, waiter_id)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.close()
                connection.close()
                return {
                    'success': True,
                    'message': 'Order-ready notification already pending',
                    'notification_id': existing['id'],
                    'waiter_id': waiter_id,
                    'duplicate': True
                }

            cursor.execute(
                """
                INSERT INTO waiter_notifications
                    (hotel_id, order_id, table_id, waiter_id, type, status, created_at)
                VALUES
                    (%s, %s, %s, %s, 'order_ready', 'pending', NOW())
                """,
                (table_row['hotel_id'], order_id, table_id, waiter_id)
            )
            notification_id = cursor.lastrowid

            connection.commit()
            cursor.close()
            connection.close()

            return {
                'success': True,
                'message': 'Order-ready notification created',
                'notification_id': notification_id,
                'waiter_id': waiter_id,
                'duplicate': False
            }
        except Error as exc:
            print(f"[WAITER_NOTIFICATION ERROR] create_order_ready_notification: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}

    @staticmethod
    def get_pending_order_ready_notifications(waiter_id):
        """Return waiter-only pending order-ready notifications."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            WaiterNotificationService._ensure_schema(cursor)

            cursor.execute(
                """
                SELECT
                    wn.id,
                    wn.order_id,
                    wn.table_id,
                    wn.waiter_id,
                    wn.type,
                    wn.status,
                    wn.created_at,
                    t.table_number,
                    o.order_status
                FROM waiter_notifications wn
                JOIN tables t ON wn.table_id = t.id
                LEFT JOIN table_orders o ON wn.order_id = o.id
                LEFT JOIN waiter_table_assignments wta
                    ON wta.table_id = t.id
                   AND wta.waiter_id = %s
                WHERE wn.waiter_id = %s
                  AND wn.type = 'order_ready'
                  AND wn.status = 'pending'
                  AND (t.waiter_id = %s OR wta.waiter_id IS NOT NULL)
                ORDER BY wn.created_at ASC
                """,
                (waiter_id, waiter_id, waiter_id)
            )
            notifications = cursor.fetchall()

            for item in notifications:
                if item.get('created_at'):
                    item['created_at'] = item['created_at'].isoformat()

            cursor.close()
            connection.close()
            return notifications
        except Error as exc:
            print(f"[WAITER_NOTIFICATION ERROR] get_pending_order_ready_notifications: {exc}")
            return []

    @staticmethod
    def acknowledge_order_ready_notification(notification_id, waiter_id):
        """Mark an order-ready notification as completed by assigned waiter."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            WaiterNotificationService._ensure_schema(cursor)

            cursor.execute(
                """
                SELECT id, status, waiter_id
                FROM waiter_notifications
                WHERE id = %s
                  AND type = 'order_ready'
                LIMIT 1
                """,
                (notification_id,)
            )
            notification = cursor.fetchone()

            if not notification:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Notification not found'}

            if int(notification['waiter_id']) != int(waiter_id):
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Unauthorized notification access'}

            if str(notification['status']).lower() != 'pending':
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Notification already acknowledged'}

            cursor.execute(
                """
                UPDATE waiter_notifications
                SET status = 'completed',
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (notification_id,)
            )

            connection.commit()
            cursor.close()
            connection.close()
            return {'success': True, 'message': 'Notification acknowledged'}
        except Error as exc:
            print(f"[WAITER_NOTIFICATION ERROR] acknowledge_order_ready_notification: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}
