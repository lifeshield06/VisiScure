"""
Add show_waiter_tips column to hotel_modules table
This controls whether waiters can see their tip amounts
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db import get_db_connection

def add_show_waiter_tips_column():
    """Add show_waiter_tips column to hotel_modules table"""
    
    print("\n" + "="*70)
    print("ADD SHOW_WAITER_TIPS COLUMN MIGRATION")
    print("="*70 + "\n")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'hotel_modules' 
            AND COLUMN_NAME = 'show_waiter_tips'
        """)
        
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            print("✅ Column 'show_waiter_tips' already exists in hotel_modules table")
            print("   No migration needed.\n")
        else:
            print("Adding 'show_waiter_tips' column to hotel_modules table...")
            
            # Add the column
            cursor.execute("""
                ALTER TABLE hotel_modules 
                ADD COLUMN show_waiter_tips TINYINT(1) DEFAULT 1
            """)
            
            conn.commit()
            print("✅ Column added successfully!\n")
            
            # Set default value for existing hotels
            cursor.execute("""
                UPDATE hotel_modules 
                SET show_waiter_tips = 1 
                WHERE show_waiter_tips IS NULL
            """)
            
            conn.commit()
            print("✅ Default values set for existing hotels\n")
        
        # Verify the column
        cursor.execute("""
            SELECT hotel_id, show_waiter_tips 
            FROM hotel_modules 
            LIMIT 5
        """)
        
        results = cursor.fetchall()
        
        if results:
            print("Current settings:")
            print("-" * 70)
            for row in results:
                hotel_id, show_tips = row
                status = "Enabled" if show_tips else "Disabled"
                print(f"  Hotel ID {hotel_id}: {status}")
            print()
        
        cursor.close()
        conn.close()
        
        print("="*70)
        print("MIGRATION COMPLETE ✅")
        print("="*70)
        print("\nThe show_waiter_tips column is now available.")
        print("Default value: TRUE (tips visible to waiters)")
        print("\nNext steps:")
        print("1. Add toggle UI to manager dashboard")
        print("2. Test the feature from web interface")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease check your database connection and try again.\n")

if __name__ == "__main__":
    add_show_waiter_tips_column()
