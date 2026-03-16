"""
Migration: Add kitchen_unique_id column to kitchen_sections table
This migration adds a unique identifier column for simplified kitchen login
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db import get_db_connection

def migrate():
    """Add kitchen_unique_id column and populate existing records"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("[MIGRATION] Adding kitchen_unique_id column...")
        
        # Check if column already exists
        cursor.execute("SHOW COLUMNS FROM kitchen_sections LIKE 'kitchen_unique_id'")
        if cursor.fetchone():
            print("[MIGRATION] Column kitchen_unique_id already exists")
            cursor.close()
            connection.close()
            return
        
        # Add kitchen_unique_id column
        cursor.execute("""
            ALTER TABLE kitchen_sections 
            ADD COLUMN kitchen_unique_id VARCHAR(50) UNIQUE AFTER section_name
        """)
        
        print("[MIGRATION] Column added successfully")
        
        # Populate existing records with unique IDs
        cursor.execute("SELECT id FROM kitchen_sections WHERE kitchen_unique_id IS NULL")
        existing_kitchens = cursor.fetchall()
        
        if existing_kitchens:
            print(f"[MIGRATION] Populating {len(existing_kitchens)} existing records...")
            for (kitchen_id,) in existing_kitchens:
                unique_id = f"KITCHEN-{kitchen_id}"
                cursor.execute("""
                    UPDATE kitchen_sections 
                    SET kitchen_unique_id = %s 
                    WHERE id = %s
                """, (unique_id, kitchen_id))
            
            print(f"[MIGRATION] Populated {len(existing_kitchens)} records")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("[MIGRATION] Migration completed successfully!")
        
    except Exception as e:
        print(f"[MIGRATION ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
