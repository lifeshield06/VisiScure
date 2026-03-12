"""
Check Table Waiter Assignment and Fix if Needed

This script checks if a table has a waiter assigned and assigns one if missing.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db import get_db_connection

def check_table_assignment(table_id):
    """Check if table has waiter assigned"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get table info
        cursor.execute("""
            SELECT t.id, t.table_number, t.waiter_id, t.hotel_id,
                   w.name as waiter_name
            FROM tables t
            LEFT JOIN waiters w ON t.waiter_id = w.id
            WHERE t.id = %s
        """, (table_id,))
        
        table = cursor.fetchone()
        
        if not table:
            print(f"❌ Table with ID {table_id} not found!")
            cursor.close()
            conn.close()
            return None
        
        print("=" * 60)
        print("TABLE INFORMATION")
        print("=" * 60)
        print(f"Table ID: {table['id']}")
        print(f"Table Number: {table['table_number']}")
        print(f"Hotel ID: {table['hotel_id']}")
        print(f"Waiter ID: {table['waiter_id']}")
        
        if table['waiter_id']:
            print(f"✅ Waiter Assigned: {table['waiter_name']} (ID: {table['waiter_id']})")
        else:
            print("❌ No waiter assigned to this table!")
        
        cursor.close()
        conn.close()
        
        return table
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def list_available_waiters(hotel_id):
    """List all active waiters for the hotel"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, name, email, is_active
            FROM waiters
            WHERE hotel_id = %s AND (is_active = 1 OR is_active IS NULL)
            ORDER BY name
        """, (hotel_id,))
        
        waiters = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not waiters:
            print("\n❌ No active waiters found for this hotel!")
            return []
        
        print("\n" + "=" * 60)
        print("AVAILABLE WAITERS")
        print("=" * 60)
        for waiter in waiters:
            print(f"ID: {waiter['id']:<5} Name: {waiter['name']:<30} Email: {waiter['email']}")
        print("=" * 60)
        
        return waiters
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def assign_waiter_to_table(table_id, waiter_id):
    """Assign waiter to table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update table with waiter_id
        cursor.execute("""
            UPDATE tables
            SET waiter_id = %s
            WHERE id = %s
        """, (waiter_id, table_id))
        
        conn.commit()
        
        # Verify assignment
        cursor.execute("""
            SELECT t.table_number, w.name as waiter_name
            FROM tables t
            JOIN waiters w ON t.waiter_id = w.id
            WHERE t.id = %s
        """, (table_id,))
        
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            print("\n" + "=" * 60)
            print("✅ ASSIGNMENT SUCCESSFUL!")
            print("=" * 60)
            print(f"Table {result[0]} is now assigned to {result[1]} (ID: {waiter_id})")
            print("=" * 60)
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error assigning waiter: {e}")
        return False

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CHECK AND ASSIGN WAITER TO TABLE")
    print("=" * 60)
    
    # Check table 9 (the one with the error)
    table_id = 9
    
    table = check_table_assignment(table_id)
    
    if not table:
        print("\n❌ Cannot proceed - table not found")
        sys.exit(1)
    
    # If no waiter assigned, offer to assign one
    if not table['waiter_id']:
        waiters = list_available_waiters(table['hotel_id'])
        
        if not waiters:
            print("\n❌ Cannot assign waiter - no active waiters available")
            print("💡 Please create a waiter first using the Manager Dashboard")
            sys.exit(1)
        
        print(f"\n📋 Table {table['table_number']} (ID: {table_id}) needs a waiter assignment")
        print(f"🏨 Hotel ID: {table['hotel_id']}")
        
        # Auto-assign to first available waiter
        first_waiter = waiters[0]
        print(f"\n🔄 Auto-assigning to: {first_waiter['name']} (ID: {first_waiter['id']})")
        
        success = assign_waiter_to_table(table_id, first_waiter['id'])
        
        if success:
            print("\n✅ Table is now ready for waiter calls!")
            print(f"💡 Waiter can login at: http://localhost:5000/waiter/login-page")
        else:
            print("\n❌ Assignment failed")
            sys.exit(1)
    else:
        print("\n✅ Table already has a waiter assigned - no action needed")
    
    print("\n" + "=" * 60)
