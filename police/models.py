from database.db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


class PoliceStation:
    @staticmethod
    def create_tables():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS police_stations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                station_name VARCHAR(255) NOT NULL,
                location VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS police_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                police_id VARCHAR(50) NOT NULL,
                station_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (station_id) REFERENCES police_stations(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS police_access_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                police_user_id INT NOT NULL,
                action VARCHAR(255) NOT NULL,
                ip_address VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (police_user_id) REFERENCES police_users(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, station_name, location, created_at FROM police_stations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def add(station_name, location):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO police_stations (station_name, location) VALUES (%s, %s)",
            (station_name, location)
        )
        conn.commit()
        cursor.close()
        conn.close()


class PoliceUser:
    def __init__(self, id, username, police_id, station_id, station_name=None):
        self.id = id
        self.username = username
        self.police_id = police_id
        self.station_id = station_id
        self.station_name = station_name

    @staticmethod
    def add(username, password, police_id, station_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO police_users (username, password, police_id, station_id) VALUES (%s, %s, %s, %s)",
            (username, hashed, police_id, station_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pu.id, pu.username, pu.police_id, ps.station_name, pu.created_at
            FROM police_users pu
            JOIN police_stations ps ON pu.station_id = ps.id
            ORDER BY pu.created_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def authenticate(username, password):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pu.id, pu.username, pu.password, pu.police_id, pu.station_id, ps.station_name
            FROM police_users pu
            JOIN police_stations ps ON pu.station_id = ps.id
            WHERE pu.username = %s
        """, (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and check_password_hash(row[2], password):
            return PoliceUser(id=row[0], username=row[1], police_id=row[3],
                              station_id=row[4], station_name=row[5])
        return None

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pu.id, pu.username, pu.police_id, pu.station_id, ps.station_name
            FROM police_users pu
            JOIN police_stations ps ON pu.station_id = ps.id
            WHERE pu.id = %s
        """, (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return PoliceUser(id=row[0], username=row[1], police_id=row[2],
                              station_id=row[3], station_name=row[4])
        return None

    @staticmethod
    def log_action(police_user_id, action, ip_address=None):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO police_access_logs (police_user_id, action, ip_address) VALUES (%s, %s, %s)",
                (police_user_id, action, ip_address)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass
