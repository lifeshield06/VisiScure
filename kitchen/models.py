"""
Kitchen authentication and management models
"""
from database.db import get_db_connection
import hashlib

class KitchenAuth:
    """Kitchen authentication and management"""
    
    @staticmethod
    def hash_password(password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def create_kitchen(hotel_id, section_name):
        """Create new kitchen with auto-generated ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Insert kitchen section (auto-increment id)
            cursor.execute("""
                INSERT INTO kitchen_sections 
                (hotel_id, section_name, is_active)
                VALUES (%s, %s, TRUE)
            """, (hotel_id, section_name))
            
            kitchen_id = cursor.lastrowid
            
            # Generate unique kitchen ID (format: KITCHEN-{id})
            kitchen_unique_id = f"KITCHEN-{kitchen_id}"
            
            # Update with unique ID
            cursor.execute("""
                UPDATE kitchen_sections 
                SET kitchen_unique_id = %s
                WHERE id = %s
            """, (kitchen_unique_id, kitchen_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print(f"[KITCHEN_AUTH] Created kitchen '{section_name}' (ID: {kitchen_unique_id})")
            
            return {
                'success': True,
                'message': 'Kitchen created successfully',
                'kitchen_id': kitchen_id,
                'kitchen_unique_id': kitchen_unique_id
            }
            
        except Exception as e:
            print(f"[KITCHEN_AUTH] Error creating kitchen: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': 'Server error'}
    
    @staticmethod
    def authenticate(kitchen_unique_id, kitchen_name):
        """Authenticate kitchen user using ID and name matching"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, hotel_id, section_name, kitchen_unique_id, is_active
                FROM kitchen_sections
                WHERE kitchen_unique_id = %s AND section_name = %s
            """, (kitchen_unique_id, kitchen_name))
            
            kitchen = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if kitchen:
                if not kitchen['is_active']:
                    return {'success': False, 'message': 'Kitchen account is inactive'}
                
                print(f"[KITCHEN_AUTH] Login successful: {kitchen_unique_id}")
                return {
                    'success': True,
                    'kitchen': kitchen
                }
            else:
                print(f"[KITCHEN_AUTH] Login failed: {kitchen_unique_id}")
                return {'success': False, 'message': 'Invalid Kitchen ID or Kitchen Name'}
                
        except Exception as e:
            print(f"[KITCHEN_AUTH] Authentication error: {e}")
            return {'success': False, 'message': 'Server error'}
    
    @staticmethod
    def get_kitchen_by_id(kitchen_id):
        """Get kitchen details by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, hotel_id, section_name, username, is_active, created_at
                FROM kitchen_sections
                WHERE id = %s
            """, (kitchen_id,))
            
            kitchen = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return kitchen
            
        except Exception as e:
            print(f"[KITCHEN_AUTH] Error getting kitchen: {e}")
            return None
    
    @staticmethod
    def get_all_kitchens(hotel_id):
        """Get all kitchens for a hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    ks.id,
                    ks.kitchen_unique_id,
                    ks.section_name,
                    ks.is_active,
                    ks.created_at,
                    GROUP_CONCAT(c.name SEPARATOR ', ') as categories
                FROM kitchen_sections ks
                LEFT JOIN kitchen_category_mapping kcm ON ks.id = kcm.kitchen_section_id
                LEFT JOIN menu_categories c ON kcm.category_id = c.id
                WHERE ks.hotel_id = %s
                GROUP BY ks.id
                ORDER BY ks.created_at DESC
            """, (hotel_id,))
            
            kitchens = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            return kitchens
            
        except Exception as e:
            print(f"[KITCHEN_AUTH] Error getting kitchens: {e}")
            return []
    
    @staticmethod
    def update_kitchen(kitchen_id, section_name):
        """Update kitchen details"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Update kitchen section name
            cursor.execute("""
                UPDATE kitchen_sections
                SET section_name = %s
                WHERE id = %s
            """, (section_name, kitchen_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Kitchen updated successfully'}
            
        except Exception as e:
            print(f"[KITCHEN_AUTH] Error updating kitchen: {e}")
            return {'success': False, 'message': 'Server error'}
    
    @staticmethod
    def toggle_active(kitchen_id):
        """Toggle kitchen active status"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                UPDATE kitchen_sections
                SET is_active = NOT is_active
                WHERE id = %s
            """, (kitchen_id,))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Kitchen status updated'}
            
        except Exception as e:
            print(f"[KITCHEN_AUTH] Error toggling status: {e}")
            return {'success': False, 'message': 'Server error'}
    
    @staticmethod
    def delete_kitchen(kitchen_id):
        """Delete kitchen (cascades to mappings and order_items)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("DELETE FROM kitchen_sections WHERE id = %s", (kitchen_id,))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Kitchen deleted successfully'}
            
        except Exception as e:
            print(f"[KITCHEN_AUTH] Error deleting kitchen: {e}")
            return {'success': False, 'message': 'Server error'}
