"""
Migration: Add logo column to hotels table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def migrate():
    """Add logo column to hotels table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'logo'")
        if cursor.fetchone():
            print("✓ Logo column already exists")
            cursor.close()
            conn.close()
            return
        
        # Add logo column
        cursor.execute("ALTER TABLE hotels ADD COLUMN logo VARCHAR(255) DEFAULT NULL")
        conn.commit()
        
        print("✓ Successfully added logo column to hotels table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error adding logo column: {e}")
        raise

if __name__ == "__main__":
    migrate()
