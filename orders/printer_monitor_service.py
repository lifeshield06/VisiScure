"""
Real-Time Printer Connection Monitoring Service
Handles continuous printer status checking, history tracking, and state change detection.
"""

import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

from database.db import get_db_connection


class PrinterStatus(Enum):
    """Printer connection states"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    CHECKING = "CHECKING"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class PrinterMonitor:
    """Real-time printer status monitoring service"""
    
    _instance = None
    _lock = threading.Lock()
    _monitoring_active = False
    _monitor_thread = None
    _printer_states = {}  # Cache of current printer states
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            self._ensure_schema()
            self._load_last_states()
        except Exception as e:
            print(f"[PrinterMonitor] Initialization error (non-critical): {e}")
            # Continue even if initialization fails - will retry on first use
    
    @staticmethod
    def _ensure_schema():
        """Create required database tables"""
        try:
            connection = get_db_connection()
        except Exception as e:
            print(f"[PrinterMonitor] Could not connect to database for schema: {e}")
            return
        
        cursor = connection.cursor()
        try:
            # Printer status history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS printer_status_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    printer_name VARCHAR(255) NOT NULL,
                    hotel_id INT,
                    section_name VARCHAR(100),
                    status ENUM('CONNECTED', 'DISCONNECTED', 'ERROR', 'CHECKING', 'NOT_CONFIGURED') NOT NULL,
                    message TEXT,
                    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_printer_name (printer_name),
                    INDEX idx_hotel_id (hotel_id),
                    INDEX idx_status (status),
                    INDEX idx_timestamp (check_timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            # Printer connection alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS printer_alerts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    printer_name VARCHAR(255) NOT NULL,
                    hotel_id INT,
                    alert_type ENUM('CONNECTED', 'DISCONNECTED', 'ERROR') NOT NULL,
                    message TEXT,
                    is_resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL,
                    INDEX idx_printer_name (printer_name),
                    INDEX idx_hotel_id (hotel_id),
                    INDEX idx_is_resolved (is_resolved),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            # Printer configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS printer_config (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT NOT NULL,
                    printer_name VARCHAR(255) NOT NULL,
                    section_name VARCHAR(100),
                    is_primary BOOLEAN DEFAULT FALSE,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    check_interval_seconds INT DEFAULT 10,
                    last_check TIMESTAMP NULL,
                    last_status ENUM('CONNECTED', 'DISCONNECTED', 'ERROR', 'CHECKING', 'NOT_CONFIGURED') DEFAULT 'CHECKING',
                    consecutive_failures INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_hotel_printer (hotel_id, printer_name),
                    INDEX idx_hotel_id (hotel_id),
                    INDEX idx_is_enabled (is_enabled),
                    INDEX idx_last_check (last_check)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            connection.commit()
            print("[PrinterMonitor] Schema initialized successfully")
        except Exception as e:
            print(f"[PrinterMonitor Schema Error] {e}")
            try:
                connection.rollback()
            except:
                pass
        finally:
            try:
                cursor.close()
                connection.close()
            except:
                pass
    
    def _load_last_states(self):
        """Load last known printer states from database"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT printer_name, last_status
                FROM printer_config
                WHERE is_enabled = TRUE
                ORDER BY last_check DESC
            """)
            
            rows = cursor.fetchall()
            for row in rows:
                self._printer_states[row['printer_name']] = {
                    'status': row['last_status'],
                    'last_updated': datetime.now().isoformat(),
                    'confidence': 0.5
                }
            
            cursor.close()
            connection.close()
        except Exception as e:
            print(f"[PrinterMonitor] Load States Error (non-critical): {e}")
    
    @staticmethod
    def check_single_printer(printer_name: str) -> Dict:
        """Check single printer connection status"""
        if not printer_name:
            return {
                'printer_name': printer_name,
                'status': PrinterStatus.NOT_CONFIGURED.value,
                'message': 'Printer not configured',
                'connected': False,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            import win32print  # type: ignore
            
            try:
                # Try to open printer (lightweight connectivity test)
                hprinter = win32print.OpenPrinter(printer_name)
                win32print.ClosePrinter(hprinter)
                
                return {
                    'printer_name': printer_name,
                    'status': PrinterStatus.CONNECTED.value,
                    'message': 'Ready to Print',
                    'connected': True,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as conn_error:
                # Printer offline or not found
                error_msg = str(conn_error)[:150]
                return {
                    'printer_name': printer_name,
                    'status': PrinterStatus.DISCONNECTED.value,
                    'message': f'Printer offline or not found: {error_msg}',
                    'connected': False,
                    'timestamp': datetime.now().isoformat()
                }
        except ImportError:
            return {
                'printer_name': printer_name,
                'status': PrinterStatus.ERROR.value,
                'message': 'pywin32 library not installed',
                'connected': False,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'printer_name': printer_name,
                'status': PrinterStatus.ERROR.value,
                'message': f'Error checking printer: {str(e)[:150]}',
                'connected': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def log_printer_status(self, printer_name: str, status: str, message: str = None, 
                          hotel_id: int = None, section_name: str = None):
        """Log printer status check result to database"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO printer_status_history 
                (printer_name, hotel_id, section_name, status, message)
                VALUES (%s, %s, %s, %s, %s)
            """, (printer_name, hotel_id, section_name, status, message))
            
            # Update printer config
            cursor.execute("""
                UPDATE printer_config
                SET last_check = NOW(), last_status = %s, consecutive_failures = 
                    CASE WHEN %s = 'CONNECTED' THEN 0 ELSE consecutive_failures + 1 END
                WHERE printer_name = %s AND hotel_id = %s
                LIMIT 1
            """, (status, status, printer_name, hotel_id))
            
            # If no rows updated, insert new config
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO printer_config 
                    (hotel_id, printer_name, section_name, last_check, last_status)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (hotel_id, printer_name, section_name, status))
            
            connection.commit()
            cursor.close()
            connection.close()
        except Exception as e:
            print(f"[PrinterMonitor Log Error] {e}")
    
    def create_alert_if_state_changed(self, printer_name: str, new_status: str, 
                                     hotel_id: int = None, message: str = None):
        """Create alert if printer status changed"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get last status
            cursor.execute("""
                SELECT last_status FROM printer_config
                WHERE printer_name = %s AND hotel_id = %s
                ORDER BY last_check DESC LIMIT 1
            """, (printer_name, hotel_id))
            
            row = cursor.fetchone()
            last_status = row['last_status'] if row else None
            
            # Check if state changed
            if last_status and last_status != new_status:
                alert_type = None
                if new_status == PrinterStatus.CONNECTED.value:
                    alert_type = 'CONNECTED'
                elif new_status == PrinterStatus.DISCONNECTED.value:
                    alert_type = 'DISCONNECTED'
                elif new_status == PrinterStatus.ERROR.value:
                    alert_type = 'ERROR'
                
                if alert_type:
                    # Close previous unresolved alerts of same type
                    cursor.execute("""
                        UPDATE printer_alerts
                        SET is_resolved = TRUE, resolved_at = NOW()
                        WHERE printer_name = %s AND hotel_id = %s 
                        AND alert_type = %s AND is_resolved = FALSE
                    """, (printer_name, hotel_id, alert_type))
                    
                    # Create new alert
                    cursor.execute("""
                        INSERT INTO printer_alerts 
                        (printer_name, hotel_id, alert_type, message)
                        VALUES (%s, %s, %s, %s)
                    """, (printer_name, hotel_id, alert_type, message or f'Printer is {alert_type.lower()}'))
            
            connection.commit()
            cursor.close()
            connection.close()
        except Exception as e:
            print(f"[PrinterMonitor Alert Error] {e}")
    
    def get_current_status(self, printer_name: str = None, hotel_id: int = None) -> Dict:
        """Get current status of printer(s)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = "SELECT * FROM printer_config WHERE is_enabled = TRUE"
            params = []
            
            if printer_name:
                query += " AND printer_name = %s"
                params.append(printer_name)
            
            if hotel_id:
                query += " AND hotel_id = %s"
                params.append(hotel_id)
            
            cursor.execute(query, tuple(params))
            configs = cursor.fetchall()
            cursor.close()
            connection.close()
            
            result = []
            for config in configs:
                result.append({
                    'printer_name': config['printer_name'],
                    'section_name': config['section_name'],
                    'status': config['last_status'],
                    'connected': config['last_status'] == PrinterStatus.CONNECTED.value,
                    'last_check': config['last_check'].isoformat() if config['last_check'] else None,
                    'consecutive_failures': config['consecutive_failures'],
                    'updated_at': config['updated_at'].isoformat() if config['updated_at'] else None
                })
            
            return {
                'success': True,
                'printers': result,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'printers': []
            }
    
    def get_alerts(self, hotel_id: int = None, unresolved_only: bool = True) -> List[Dict]:
        """Get printer alerts"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = "SELECT * FROM printer_alerts WHERE 1=1"
            params = []
            
            if hotel_id:
                query += " AND hotel_id = %s"
                params.append(hotel_id)
            
            if unresolved_only:
                query += " AND is_resolved = FALSE"
            
            query += " ORDER BY created_at DESC LIMIT 100"
            
            cursor.execute(query, tuple(params))
            alerts = cursor.fetchall()
            cursor.close()
            connection.close()
            
            result = []
            for alert in alerts:
                result.append({
                    'id': alert['id'],
                    'printer_name': alert['printer_name'],
                    'alert_type': alert['alert_type'],
                    'message': alert['message'],
                    'is_resolved': alert['is_resolved'],
                    'created_at': alert['created_at'].isoformat(),
                    'resolved_at': alert['resolved_at'].isoformat() if alert['resolved_at'] else None
                })
            
            return result
        except Exception as e:
            print(f"[PrinterMonitor Get Alerts Error] {e}")
            return []
    
    def get_status_history(self, printer_name: str = None, hotel_id: int = None, 
                          hours: int = 24) -> List[Dict]:
        """Get printer status history"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT * FROM printer_status_history
                WHERE check_timestamp > DATE_SUB(NOW(), INTERVAL %s HOUR)
            """
            params = [hours]
            
            if printer_name:
                query += " AND printer_name = %s"
                params.append(printer_name)
            
            if hotel_id:
                query += " AND hotel_id = %s"
                params.append(hotel_id)
            
            query += " ORDER BY check_timestamp DESC LIMIT 500"
            
            cursor.execute(query, tuple(params))
            history = cursor.fetchall()
            cursor.close()
            connection.close()
            
            result = []
            for record in history:
                result.append({
                    'printer_name': record['printer_name'],
                    'status': record['status'],
                    'message': record['message'],
                    'timestamp': record['check_timestamp'].isoformat()
                })
            
            return result
        except Exception as e:
            print(f"[PrinterMonitor History Error] {e}")
            return []
    
    def start_monitoring(self, check_interval: int = 10):
        """Start background printer monitoring thread"""
        if self._monitoring_active:
            print("[PrinterMonitor] Monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(check_interval,),
            daemon=True,
            name="PrinterMonitorThread"
        )
        self._monitor_thread.start()
        print(f"[PrinterMonitor] Background monitoring started (interval: {check_interval}s)")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("[PrinterMonitor] Monitoring stopped")
    
    def _monitor_loop(self, check_interval: int):
        """Background monitoring loop"""
        while self._monitoring_active:
            try:
                self._do_full_check()
                time.sleep(check_interval)
            except Exception as e:
                print(f"[PrinterMonitor Loop Error] {e}")
                time.sleep(check_interval)
    
    def _do_full_check(self):
        """Check all configured printers"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT * FROM printer_config 
                WHERE is_enabled = TRUE
                AND (last_check IS NULL OR last_check < DATE_SUB(NOW(), INTERVAL check_interval_seconds SECOND))
            """)
            
            printers = cursor.fetchall()
            cursor.close()
            connection.close()
            
            for printer_cfg in printers:
                printer_name = printer_cfg['printer_name']
                hotel_id = printer_cfg['hotel_id']
                section_name = printer_cfg['section_name']
                
                # Check printer status
                result = self.check_single_printer(printer_name)
                new_status = result['status']
                message = result['message']
                
                # Log status
                self.log_printer_status(printer_name, new_status, message, hotel_id, section_name)
                
                # Create alert if state changed
                self.create_alert_if_state_changed(printer_name, new_status, hotel_id, message)
                
                # Update cache
                self._printer_states[printer_name] = {
                    'status': new_status,
                    'last_updated': datetime.now().isoformat(),
                    'message': message,
                    'connected': result['connected']
                }
                
                print(f"[PrinterMonitor] {printer_name}: {new_status}")
        
        except Exception as e:
            print(f"[PrinterMonitor Full Check Error] {e}")


# Global monitor instance - lazy initialized
_printer_monitor = None
_printer_monitor_lock = threading.Lock()


def get_printer_monitor() -> PrinterMonitor:
    """Get or create the printer monitor instance (lazy initialization)"""
    global _printer_monitor
    if _printer_monitor is None:
        with _printer_monitor_lock:
            if _printer_monitor is None:
                try:
                    _printer_monitor = PrinterMonitor()
                except Exception as e:
                    print(f"[PrinterMonitor] Deferred initialization: {e}")
                    # Return a mock instance that won't crash on access
                    _printer_monitor = PrinterMonitor.__new__(PrinterMonitor)
                    _printer_monitor._initialized = False
    return _printer_monitor


# Lazy proxy for backward compatibility
class PrinterMonitorProxy:
    """Proxy that lazily initializes PrinterMonitor"""
    def __getattr__(self, name):
        return getattr(get_printer_monitor(), name)


printer_monitor = PrinterMonitorProxy()


def register_printer(hotel_id: int, printer_name: str, section_name: str = None, 
                    is_primary: bool = False, check_interval: int = 10):
    """Register a printer for monitoring"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO printer_config 
            (hotel_id, printer_name, section_name, is_primary, check_interval_seconds, last_status)
            VALUES (%s, %s, %s, %s, %s, 'CHECKING')
            ON DUPLICATE KEY UPDATE
            is_enabled = TRUE, check_interval_seconds = %s
        """, (hotel_id, printer_name, section_name, is_primary, check_interval, check_interval))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"[PrinterMonitor] Registered printer: {printer_name}")
        return True
    except Exception as e:
        print(f"[PrinterMonitor Register Error] {e}")
        return False
