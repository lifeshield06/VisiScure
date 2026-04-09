import os
from datetime import datetime
from typing import Dict, List, Tuple

from database.db import get_db_connection


class KOTService:
    """Kitchen Order Ticket auto-print service for 58mm ESC/POS printers."""

    _schema_checked = False

    @staticmethod
    def _sanitize_section_key(section_name: str) -> str:
        return ''.join(ch if ch.isalnum() else '_' for ch in (section_name or 'GENERAL').upper())

    @staticmethod
    def _safe_text(value, fallback='-') -> str:
        text = str(value).strip() if value is not None else ''
        return text if text else fallback

    @staticmethod
    def _fit_line(left: str, right: str, width: int = 32) -> str:
        left = str(left)
        right = str(right)
        if len(left) + len(right) + 1 > width:
            left = left[: max(0, width - len(right) - 1)]
        spaces = ' ' * max(1, width - len(left) - len(right))
        return f"{left}{spaces}{right}"

    @staticmethod
    def _chunks(text: str, width: int = 32) -> List[str]:
        text = (text or '').strip()
        if not text:
            return ['']
        words = text.split()
        lines = []
        current = ''
        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= width:
                current = f"{current} {word}"
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _get_printer_name(section_name: str) -> str:
        section_key = KOTService._sanitize_section_key(section_name)
        section_printer = os.getenv(f'KOT_PRINTER_{section_key}', '').strip()
        if section_printer:
            return section_printer
        return os.getenv('KOT_PRINTER_DEFAULT', '').strip()

    @staticmethod
    def _build_kot_text(hotel_name: str, section_name: str, kot_number: str, table_number: str,
                        order_time: datetime, items: List[Dict], note: str = None) -> str:
        width = 32
        lines = []
        lines.append(KOTService._safe_text(hotel_name, 'TIP TOP HOTEL'))
        lines.append(f"SECTION: {KOTService._safe_text(section_name, 'GENERAL')}")
        lines.append(f"KOT: {kot_number}")
        lines.append(KOTService._fit_line(f"TABLE: {table_number}", order_time.strftime('%I:%M %p'), width))
        lines.append('-' * width)

        for item in items:
            item_name = KOTService._safe_text(item.get('dish_name') or item.get('item_name'), 'Item')
            qty = int(item.get('quantity') or 0)
            item_line = f"{item_name} x {qty}"
            for line in KOTService._chunks(item_line, width):
                lines.append(line)

        if note:
            lines.append('-' * width)
            lines.append('NOTE:')
            for line in KOTService._chunks(note, width):
                lines.append(line)

        lines.append('-' * width)
        lines.append('')
        return '\n'.join(lines)

    @staticmethod
    def _print_escpos(printer_name: str, text: str) -> Tuple[bool, str]:
        if not printer_name:
            return False, 'Printer not configured. Set KOT_PRINTER_DEFAULT or section-specific printer env.'

        try:
            import win32print  # type: ignore

            # ESC/POS: Initialize, feed, cut
            payload = b'\x1b@' + text.encode('ascii', errors='replace') + b'\n\n\n\x1dV\x00'
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(hprinter, 1, ('KOT Print', None, 'RAW'))
                try:
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, payload)
                    win32print.EndPagePrinter(hprinter)
                finally:
                    win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)

            return True, 'Printed successfully'
        except ImportError:
            return False, 'pywin32 not installed for RAW printer communication'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ensure_schema():
        if KOTService._schema_checked:
            return

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kitchen_kot_tickets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    kot_number VARCHAR(50) NOT NULL,
                    hotel_id INT,
                    order_id INT,
                    table_id INT,
                    session_id VARCHAR(100),
                    section_id INT,
                    section_name VARCHAR(100),
                    note TEXT,
                    print_status ENUM('PENDING', 'PRINTED', 'FAILED') DEFAULT 'PENDING',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    printed_at TIMESTAMP NULL,
                    INDEX idx_kot_order (order_id),
                    INDEX idx_kot_hotel (hotel_id),
                    INDEX idx_kot_status (print_status)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kitchen_kot_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    kot_ticket_id INT NOT NULL,
                    order_item_id INT NOT NULL,
                    item_name VARCHAR(255),
                    quantity INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_kot_item (kot_ticket_id, order_item_id),
                    INDEX idx_kot_items_order_item (order_item_id)
                )
                """
            )

            cursor.execute("SHOW COLUMNS FROM order_items LIKE 'kot_printed_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE order_items ADD COLUMN kot_printed_at DATETIME NULL")

            cursor.execute("SHOW COLUMNS FROM order_items LIKE 'kot_ticket_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE order_items ADD COLUMN kot_ticket_id INT NULL")

            connection.commit()
            KOTService._schema_checked = True
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def print_for_new_items(order_id: int, note: str = None) -> Dict:
        """Print KOTs for newly added order_items where kot_printed_at is NULL.
        Groups by kitchen section and prints one KOT per section.
        """
        auto_enabled = os.getenv('KOT_AUTO_PRINT_ENABLED', '1').strip() not in ('0', 'false', 'False')
        if not auto_enabled:
            return {'success': True, 'message': 'KOT auto-print disabled', 'printed': 0, 'failed': 0}

        if not order_id:
            return {'success': False, 'message': 'order_id required'}

        KOTService.ensure_schema()

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        printed_count = 0
        failed_count = 0
        details = []

        try:
            cursor.execute(
                """
                SELECT o.id as order_id,
                       o.hotel_id,
                       o.table_id,
                       o.session_id,
                       o.created_at,
                       COALESCE(CAST(t.table_number AS CHAR), 'Table Deleted') as table_number,
                       h.hotel_name,
                       oi.id as order_item_id,
                       oi.dish_name,
                       oi.quantity,
                       oi.kitchen_section_id,
                       COALESCE(ks.section_name, 'GENERAL') as section_name
                FROM table_orders o
                LEFT JOIN tables t ON o.table_id = t.id
                LEFT JOIN hotels h ON h.id = o.hotel_id
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN kitchen_sections ks ON ks.id = oi.kitchen_section_id
                WHERE o.id = %s
                  AND oi.kot_printed_at IS NULL
                ORDER BY oi.id ASC
                """,
                (order_id,)
            )
            rows = cursor.fetchall() or []

            if not rows:
                return {'success': True, 'message': 'No new items for KOT', 'printed': 0, 'failed': 0}

            groups = {}
            for row in rows:
                key = (row.get('kitchen_section_id') or 0, row.get('section_name') or 'GENERAL')
                groups.setdefault(key, []).append(row)

            for (section_id, section_name), items in groups.items():
                base = items[0]

                # Create ticket row first to get numeric sequence.
                cursor.execute(
                    """
                    INSERT INTO kitchen_kot_tickets
                    (kot_number, hotel_id, order_id, table_id, session_id, section_id, section_name, note, print_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
                    """,
                    ('PENDING', base.get('hotel_id'), base.get('order_id'), base.get('table_id'),
                     base.get('session_id'), section_id if section_id != 0 else None, section_name, note)
                )
                ticket_id = cursor.lastrowid
                kot_number = f"KOT-{ticket_id:06d}"
                cursor.execute("UPDATE kitchen_kot_tickets SET kot_number = %s WHERE id = %s", (kot_number, ticket_id))

                for item in items:
                    cursor.execute(
                        """
                        INSERT INTO kitchen_kot_items (kot_ticket_id, order_item_id, item_name, quantity)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (ticket_id, item['order_item_id'], item.get('dish_name'), item.get('quantity') or 1)
                    )

                ticket_text = KOTService._build_kot_text(
                    hotel_name=base.get('hotel_name') or 'Tip Top Hotel',
                    section_name=section_name,
                    kot_number=kot_number,
                    table_number=KOTService._safe_text(base.get('table_number'), 'Table Deleted'),
                    order_time=base.get('created_at') or datetime.now(),
                    items=items,
                    note=note,
                )

                printer_name = KOTService._get_printer_name(section_name)
                ok, message = KOTService._print_escpos(printer_name, ticket_text)

                if ok:
                    printed_count += 1
                    cursor.execute(
                        """
                        UPDATE kitchen_kot_tickets
                        SET print_status = 'PRINTED', printed_at = NOW(), error_message = NULL
                        WHERE id = %s
                        """,
                        (ticket_id,)
                    )
                    order_item_ids = [item['order_item_id'] for item in items]
                    placeholders = ','.join(['%s'] * len(order_item_ids))
                    cursor.execute(
                        f"UPDATE order_items SET kot_printed_at = NOW(), kot_ticket_id = %s WHERE id IN ({placeholders})",
                        tuple([ticket_id] + order_item_ids)
                    )
                else:
                    failed_count += 1
                    cursor.execute(
                        """
                        UPDATE kitchen_kot_tickets
                        SET print_status = 'FAILED', error_message = %s
                        WHERE id = %s
                        """,
                        (message[:1000], ticket_id)
                    )

                details.append({
                    'ticket_id': ticket_id,
                    'kot_number': kot_number,
                    'section': section_name,
                    'printer': printer_name,
                    'success': ok,
                    'message': message,
                    'items': len(items),
                })

            connection.commit()
            return {
                'success': True,
                'message': 'KOT processing completed',
                'printed': printed_count,
                'failed': failed_count,
                'details': details,
            }
        except Exception as e:
            connection.rollback()
            return {'success': False, 'message': f'KOT processing failed: {e}'}
        finally:
            cursor.close()
            connection.close()
