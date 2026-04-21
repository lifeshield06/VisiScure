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
    """Ensure kitchen_unique_id is numeric and migrate legacy KITCHEN-* values."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("[MIGRATION] Ensuring kitchen_unique_id column exists...")
        
        # Check if column already exists
        cursor.execute("SHOW COLUMNS FROM kitchen_sections LIKE 'kitchen_unique_id'")
        column = cursor.fetchone()
        if not column:
            # Add kitchen_unique_id column
            cursor.execute("""
                ALTER TABLE kitchen_sections 
                ADD COLUMN kitchen_unique_id INT NULL AFTER section_name
            """)
            print("[MIGRATION] Column added successfully as INT")
        else:
            print("[MIGRATION] Column kitchen_unique_id already exists")
        
        # Populate/normalize all records with numeric IDs.
        cursor.execute("SELECT id, kitchen_unique_id FROM kitchen_sections")
        existing_kitchens = cursor.fetchall()
        
        if existing_kitchens:
            print(f"[MIGRATION] Normalizing {len(existing_kitchens)} records...")
            used_ids = set()
            for kitchen_id, raw_unique_id in existing_kitchens:
                normalized_id = kitchen_id

                if raw_unique_id is not None:
                    raw_text = str(raw_unique_id).strip()
                    if raw_text:
                        cleaned = raw_text.upper().replace('KITCHEN-', '', 1).strip()
                        if cleaned.isdigit():
                            normalized_id = int(cleaned)

                # Keep IDs unique and positive during migration.
                if normalized_id <= 0 or normalized_id in used_ids:
                    normalized_id = kitchen_id

                while normalized_id in used_ids:
                    normalized_id += 1

                used_ids.add(normalized_id)

                cursor.execute("""
                    UPDATE kitchen_sections 
                    SET kitchen_unique_id = %s 
                    WHERE id = %s
                """, (normalized_id, kitchen_id))
            
            print(f"[MIGRATION] Normalized {len(existing_kitchens)} records")

        # Ensure INT type
        cursor.execute("""
            ALTER TABLE kitchen_sections
            MODIFY COLUMN kitchen_unique_id INT NULL
        """)

        # Ensure unique index exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'kitchen_sections'
              AND COLUMN_NAME = 'kitchen_unique_id'
              AND NON_UNIQUE = 0
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE kitchen_sections
                ADD UNIQUE KEY unique_kitchen_unique_id (kitchen_unique_id)
            """)
            print("[MIGRATION] Added UNIQUE index on kitchen_unique_id")
        
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
