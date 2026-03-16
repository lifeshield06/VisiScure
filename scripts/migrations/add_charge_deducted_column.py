"""
Migration script to add charge_deducted column to table_orders table
This ensures the column exists for tracking per-order charge deductions
"""

from database.db import get_db_connection

def add_charge_deducted_column():
    """Add charge_deducted column to table_orders if it doesn't exist"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'table_orders'
            AND COLUMN_NAME = 'charge_deducted'
        """)
        
        result = cursor.fetchone()
        column_exists = result[0] > 0 if result else False
        
        if column_exists:
            print("✅ Column 'charge_deducted' already exists in table_orders")
        else:
            print("Adding 'charge_deducted' column to table_orders...")
            
            cursor.execute("""
                ALTER TABLE table_orders
                ADD COLUMN charge_deducted BOOLEAN DEFAULT FALSE
            """)
            
            connection.commit()
            print("✅ Column 'charge_deducted' added successfully to table_orders")
        
        cursor.close()
        connection.close()
        
        return True
    except Exception as e:
        print(f"❌ Error adding charge_deducted column: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("MIGRATION: Add charge_deducted Column to table_orders")
    print("="*60 + "\n")
    
    success = add_charge_deducted_column()
    
    if success:
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ MIGRATION FAILED")
        print("="*60)
