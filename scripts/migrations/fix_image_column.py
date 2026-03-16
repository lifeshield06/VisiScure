"""Script to add image_path column to daily_special_menu table"""
from database.db import get_db_connection

def fix_column():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'daily_special_menu' 
            AND COLUMN_NAME = 'image_path'
        """)
        exists = cursor.fetchone()
        
        if exists:
            print("✓ Column 'image_path' already exists in daily_special_menu table")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE daily_special_menu 
                ADD COLUMN image_path VARCHAR(500) DEFAULT NULL AFTER price
            """)
            conn.commit()
            print("✓ Successfully added 'image_path' column to daily_special_menu table")
        
        cursor.close()
        conn.close()
        print("Database fix completed!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_column()
