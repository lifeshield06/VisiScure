"""
Fix Waiter Call Issue - Comprehensive Solution

This script:
1. Shows all tables with their IDs and assignments
2. Identifies which table you're trying to access
3. Ensures that table has a waiter assigned
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db import get_db_connection

def show_table_access_info():
    """Show how to access each table via URL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT t.id, t.table_number, t.waiter_id, t.hotel_id,
                   w.name as waiter_name
            FROM tables t
            LEFT JOIN waiters w ON t.waiter_id = w.id
            ORDER BY t.hotel_id, t.table_number
        """)
        
        tables = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print("=" * 100)
        print("TABLE ACCESS INFORMATION")
        print("=" * 100)
        print(f"{'Table#':<10} {'DB ID':<10} {'Hotel':<10} {'Waiter':<25} {'Access URL':<40}")
        print("-" * 100)
        
        for table in tables:
            waiter_info = f"{table['waiter_name']} (ID:{table['waiter_id']})" if table['waiter_name'] else "❌ NOT ASSIGNED"
<<<<<<< HEAD
            url = f"http://127.0.0.1:5000/orders/menu/{table['id']}"
=======
            url = f"http://localhost:5000/orders/menu/{table['id']}"
>>>>>>> 4874e11764932e9b9ef1fa14498af6898579bbc5
            status = "✅" if table['waiter_id'] else "❌"
            print(f"{status} T{table['table_number']:<7} {table['id']:<10} {table['hotel_id']:<10} {waiter_info:<25} {url:<40}")
        
        print("=" * 100)
        
        # Show unassigned tables
        unassigned = [t for t in tables if not t['waiter_id']]
        if unassigned:
            print(f"\n⚠️  WARNING: {len(unassigned)} table(s) without waiter - Call Waiter button will NOT work!")
            for t in unassigned:
<<<<<<< HEAD
                print(f"   ❌ Table {t['table_number']} - Access at: http://127.0.0.1:5000/orders/menu/{t['id']}")
=======
                print(f"   ❌ Table {t['table_number']} - Access at: http://localhost:5000/orders/menu/{t['id']}")
>>>>>>> 4874e11764932e9b9ef1fa14498af6898579bbc5
        else:
            print("\n✅ All tables have waiters assigned - Call Waiter button will work!")
        
        return tables
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def fix_all_tables():
    """Assign waiters to all tables that don't have one"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all tables without waiters
        cursor.execute("""
            SELECT t.id, t.table_number, t.hotel_id
            FROM tables t
            WHERE t.waiter_id IS NULL
        """)
        
        unassigned = cursor.fetchall()
        
        if not unassigned:
            print("\n✅ No tables need fixing!")
            cursor.close()
            conn.close()
            return True
        
        print(f"\n🔧 Fixing {len(unassigned)} table(s)...")
        print("=" * 100)
        
        fixed_count = 0
        for table in unassigned:
            # Find a waiter for this hotel
            cursor.execute("""
                SELECT id, name
                FROM waiters
                WHERE hotel_id = %s AND (is_active = 1 OR is_active IS NULL)
                ORDER BY id
                LIMIT 1
            """, (table['hotel_id'],))
            
            waiter = cursor.fetchone()
            
            if waiter:
                cursor.execute("""
                    UPDATE tables
                    SET waiter_id = %s
                    WHERE id = %s
                """, (waiter['id'], table['id']))
                
                print(f"✅ Table {table['table_number']} (ID:{table['id']}) → {waiter['name']} (ID:{waiter['id']})")
                fixed_count += 1
            else:
                print(f"❌ Table {table['table_number']} (ID:{table['id']}) - No waiter available for Hotel {table['hotel_id']}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("=" * 100)
        print(f"✅ Fixed {fixed_count} table(s)!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n" + "=" * 100)
    print("WAITER CALL SYSTEM - FIX ALL TABLES")
    print("=" * 100 + "\n")
    
    # Show current state
    print("STEP 1: Current Table Status")
    print("-" * 100)
    tables = show_table_access_info()
    
    # Check if any tables need fixing
    unassigned = [t for t in tables if not t['waiter_id']]
    
    if unassigned:
        print("\n" + "=" * 100)
        print("STEP 2: Fixing Unassigned Tables")
        print("=" * 100)
        fix_all_tables()
        
        # Show final state
        print("\n" + "=" * 100)
        print("STEP 3: Final Verification")
        print("=" * 100 + "\n")
        show_table_access_info()
    
    print("\n" + "=" * 100)
    print("✅ COMPLETE - All tables are now ready for waiter calls!")
    print("=" * 100)
    print("\n💡 IMPORTANT:")
    print("   - Use the 'Access URL' from the table above to access each table")
    print("   - The URL uses the database ID, not the table number")
    print("   - Example: Table 10 might be at /orders/menu/9 (if DB ID is 9)")
    print("\n🔄 If you still see errors:")
    print("   1. Clear your browser cache (Ctrl+Shift+Delete)")
    print("   2. Restart the Flask server")
    print("   3. Access the correct URL from the table above")
    print("=" * 100 + "\n")
