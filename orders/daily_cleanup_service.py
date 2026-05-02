import threading
from datetime import datetime, timedelta

from database.db import get_db_connection


class DailyOrderCleanupService:
    """Background cleanup service that clears order data at midnight."""

    _started = False
    _lock = threading.Lock()
    _mutex_handle = None

    @staticmethod
    def _seconds_until_midnight() -> float:
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return max(1.0, (tomorrow - now).total_seconds())

    @staticmethod
    def _cleanup_order_tables() -> bool:
        tables = [
            'kitchen_kot_items',
            'kitchen_kot_tickets',
            'waiter_notifications',
            'order_items',
            'bill_requests',
            'active_tables',
            'bills',
            'table_orders',
        ]

        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            deleted_counts = {}
            for table_name in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                deleted_counts[table_name] = cursor.fetchone()[0] or 0

            for table_name in tables:
                cursor.execute(f"DELETE FROM {table_name}")

            cursor.execute(
                """
                UPDATE tables
                SET status = 'AVAILABLE',
                    current_session_id = NULL,
                    current_guest_name = NULL
                """
            )

            connection.commit()
            print(f"[DAILY_ORDER_CLEANUP] Cleared order data: {deleted_counts}")
            return True
        except Exception as exc:
            if connection:
                try:
                    connection.rollback()
                except Exception:
                    pass
            print(f"[DAILY_ORDER_CLEANUP] Error: {exc}")
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass

    @classmethod
    def _run_loop(cls):
        while True:
            sleep_seconds = cls._seconds_until_midnight()
            print(f"[DAILY_ORDER_CLEANUP] Next cleanup in {sleep_seconds:.0f}s")
            stop_event = threading.Event()
            stop_event.wait(timeout=sleep_seconds)

            try:
                cls._cleanup_order_tables()
            except Exception as exc:
                print(f"[DAILY_ORDER_CLEANUP] Unhandled cleanup error: {exc}")

    @classmethod
    def start(cls):
        with cls._lock:
            if cls._started:
                return False

            try:
                import win32api  # type: ignore
                import win32con  # type: ignore
                import win32event  # type: ignore
                import winerror  # type: ignore

                mutex_name = "Global\\VisiScureDailyOrderCleanupScheduler"
                cls._mutex_handle = win32event.CreateMutex(None, False, mutex_name)
                last_error = win32api.GetLastError()
                if last_error == winerror.ERROR_ALREADY_EXISTS:
                    print("[DAILY_ORDER_CLEANUP] Scheduler already running in another process")
                    return False
            except Exception as exc:
                print(f"[DAILY_ORDER_CLEANUP] Mutex setup failed, continuing with local scheduler: {exc}")

            worker = threading.Thread(target=cls._run_loop, daemon=True)
            worker.start()
            cls._started = True
            print("[DAILY_ORDER_CLEANUP] Scheduler started")
            return True


def start_daily_order_cleanup_scheduler() -> bool:
    return DailyOrderCleanupService.start()