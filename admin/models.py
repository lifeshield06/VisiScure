from database.db import get_db_connection


class Admin:
    def __init__(self, id=None, name=None, username=None):
        self.id = id
        self.name = name
        self.username = username

    @staticmethod
    def authenticate(username, password):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, name, username
                FROM admins
                WHERE username = %s AND password = SHA2(%s, 256)
                """,
                (username, password)
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return Admin(id=row[0], name=row[1], username=row[2])
            return None

        except Exception as e:
            print("Admin auth error:", e)
            return None

    @staticmethod
    def update_username(admin_id, new_username):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE admins SET username = %s WHERE id = %s",
            (new_username, admin_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update_password(admin_id, new_password):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE admins SET password = SHA2(%s, 256) WHERE id = %s",
            (new_password, admin_id)
        )
        conn.commit()
        conn.close()


class Manager:
    @staticmethod
    def get_all_managers():
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.name, 
                    m.email, 
                    m.username, 
                    h.hotel_name,
                    DATE_FORMAT(m.created_at, '%Y-%m-%d %H:%i:%s') as formatted_created_at
                FROM managers m
                LEFT JOIN hotel_managers hm ON m.id = hm.manager_id
                LEFT JOIN hotels h ON hm.hotel_id = h.id
                ORDER BY m.created_at DESC
            """)
            managers = cursor.fetchall()
            conn.close()
            return managers
        except Exception as e:
            print(f"Error getting managers: {e}")
            return []
    
    @staticmethod
    def get_manager_by_id(manager_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, username FROM managers WHERE id = %s", (manager_id,))
            manager = cursor.fetchone()
            conn.close()
            return manager
        except Exception as e:
            print(f"Error getting manager: {e}")
            return None
    
    @staticmethod
    def update_manager(manager_id, name, email, username, password=None):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if password:
                cursor.execute(
                    "UPDATE managers SET name = %s, email = %s, username = %s, password = SHA2(%s, 256) WHERE id = %s",
                    (name, email, username, password, manager_id)
                )
            else:
                cursor.execute(
                    "UPDATE managers SET name = %s, email = %s, username = %s WHERE id = %s",
                    (name, email, username, manager_id)
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating manager: {e}")
            raise e
    
    @staticmethod
    def delete_manager(manager_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM managers WHERE id = %s", (manager_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error deleting manager: {e}")
            raise e

    @staticmethod
    def get_assigned_hotel(manager_id):
        """Get the hotel assigned to a manager, if any"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.id, h.hotel_name
                FROM hotel_managers hm
                JOIN hotels h ON hm.hotel_id = h.id
                WHERE hm.manager_id = %s
                LIMIT 1
            """, (manager_id,))
            result = cursor.fetchone()
            conn.close()
            return result  # (hotel_id, hotel_name) or None
        except Exception as e:
            print(f"Error getting assigned hotel: {e}")
            return None

    @staticmethod
    def assign_hotel(manager_id, hotel_id):
        """Assign a hotel to a manager"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Check if already assigned
            cursor.execute("SELECT id FROM hotel_managers WHERE manager_id = %s", (manager_id,))
            existing = cursor.fetchone()
            if existing:
                # Update existing assignment
                cursor.execute(
                    "UPDATE hotel_managers SET hotel_id = %s WHERE manager_id = %s",
                    (hotel_id, manager_id)
                )
            else:
                # Create new assignment
                cursor.execute(
                    "INSERT INTO hotel_managers (hotel_id, manager_id) VALUES (%s, %s)",
                    (hotel_id, manager_id)
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error assigning hotel: {e}")
            raise e
