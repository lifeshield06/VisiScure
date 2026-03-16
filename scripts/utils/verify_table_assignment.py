"""
Verify Table Assignment - Debug Script

Check the exact table_id being used and verify database state.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db import get_db_connection

def check_all_tables():
    """Check all tables and their waiter assignments"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT t.id, t.table_number, t.waiter_id, t.hotel_id,
                   w.name as waiter_name, w.email as waiter_email
            FROM tables t
            LEFT JOIN waiters w ON t.waiter_id = w.id
            ORDER BY t.id
        """)
        
        tables = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print("=" * 80)
        print("ALL TABLES AND WAITER ASSIGNMENTS")
        print("=" * 80)
        print(f"{'ID':<5} {'Table#':<8} {'Hotel':<8} {'Waiter ID':<12} {'Waiter Name':<30}")
        print("-" * 80)
        
        for table in tables:
            waiter_name = table['waiter_name'] if table['waiter_name'] else "❌ NOT ASSIGNED"
            waiter_id = table['waiter_id'] if table['waiter_id'] else "NULL"
            print(f"{table['id']:<5} {table['table_number']:<8} {table['hotel_id']:<8} {str(waiter_id):<12} {waiter_name:<30}")
        
        print("=" * 80)
        
        # Count unassigned tables
        unassigned = [t for t in tables if not t['waiter_id']]
        if unassigned:
            print(f"\n⚠️  {len(unassigned)} table(s) without waiter assignment:")
            for t in unassigned:
                print(f"   - Table {t['table_number']} (ID: {t['id']}, Hotel: {t['hotel_id']})")
        else:
            print("\n✅ All tables have waiters assigned!")
        
        return tables
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def assign_all_unassigned_tables():
    """Assign waiters to all unassigned tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all unassigned tables
        cursor.execute("""
            SELECT id, table_number, hotel_id
            FROM tables
            WHERE waiter_id IS NULL
        """)
        
        unassigned_tables = cursor.fetchall()
        
        if not unassigned_tables:
            print("\n✅ No unassigned tables found!")
            cursor.close()
            conn.close()
            return
        
        print(f"\n🔄 Found {len(unassigned_tables)} unassigned table(s)")
        
        # For each unassigned table, find a waiter from the same hotel
        for table in unassigned_tables:
            cursor.execute("""
                SELECT id, name
                FROM waiters
                WHERE hotel_id = %s AND (is_active = 1 OR is_active IS NULL)
                LIMIT 1
            """, (table['hotel_id'],))
            
            waiter = cursor.fetchone()
            
            if waiter:
                cursor.execute("""
                    UPDATE tables
                    SET waiter_id = %s
                    WHERE id = %s
                """, (waiter['id'], table['id']))
                
                print(f"✅ Assigned Table {table['table_number']} (ID: {table['id']}) → {waiter['name']} (ID: {waiter['id']})")
            else:
                print(f"❌ No waiter available for Table {table['table_number']} (Hotel: {table['hotel_id']})")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Assignment complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("TABLE WAITER ASSIGNMENT VERIFICATION")
    print("=" * 80 + "\n")
    
    # Check all tables
    tables = check_all_tables()
    
    # Check if there are unassigned tables
    unassigned = [t for t in tables if not t['waiter_id']]
    
    if unassigned:
        print("\n" + "=" * 80)
        print("FIXING UNASSIGNED TABLES")
        print("=" * 80)
        assign_all_unassigned_tables()
        
        # Verify again
        print("\n" + "=" * 80)
        print("VERIFICATION AFTER FIX")
        print("=" * 80 + "\n")
        check_all_tables()
    
    print("\n" + "=" * 80)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
