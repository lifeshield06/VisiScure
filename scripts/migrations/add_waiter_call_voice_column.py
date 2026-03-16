"""
Add waiter_call_voice column to hotels table

This migration adds a customizable voice message field that managers can configure
for waiter call alerts.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import get_db_connection

def run_migration():
    """Add waiter_call_voice column to hotels table"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("=" * 60)
        print("ADDING WAITER CALL VOICE MESSAGE COLUMN")
        print("=" * 60)
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'hotels' 
            AND COLUMN_NAME = 'waiter_call_voice'
        """)
        result = cursor.fetchone()
        
        if result[0] > 0:
            print("✓ Column 'waiter_call_voice' already exists")
            cursor.close()
            connection.close()
            return True
        
        # Add waiter_call_voice column
        cursor.execute("""
            ALTER TABLE hotels 
            ADD COLUMN waiter_call_voice VARCHAR(500) DEFAULT 'Table {table} is calling waiter'
        """)
        
        connection.commit()
        print("✓ Added 'waiter_call_voice' column to hotels table")
        print("✓ Default message: 'Table {table} is calling waiter'")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = run_migration()
    if success:
        print("\n✅ You can now configure voice messages in Manager Dashboard → Settings")
    else:
        print("\n❌ Migration failed. Please check the error above.")
