#!/usr/bin/env python3
"""
Test script to verify the tip system is working correctly
"""
from database.db import get_db_connection

def test_tip_system():
    """Test the tip system components"""
    print("=" * 60)
    print("TIP SYSTEM TEST")
    print("=" * 60)
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Test 1: Check if waiter_tips table exists
        print("\n[TEST 1] Checking waiter_tips table...")
        cursor.execute("SHOW TABLES LIKE 'waiter_tips'")
        waiter_tips_exists = cursor.fetchone() is not None
        print(f"waiter_tips table exists: {waiter_tips_exists}")
        
        if waiter_tips_exists:
            cursor.execute("DESCRIBE waiter_tips")
            columns = cursor.fetchall()
            print("Table structure:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
        
        # Test 2: Check waiters
        print("\n[TEST 2] Checking waiters...")
        cursor.execute("SELECT id, name, hotel_id FROM waiters LIMIT 5")
        waiters = cursor.fetchall()
        print(f"Found {len(waiters)} waiters:")
        for waiter in waiters:
            print(f"  - {waiter['name']} (ID: {waiter['id']}, Hotel: {waiter['hotel_id']})")
        
        # Test 3: Check waiter table assignments
        print("\n[TEST 3] Checking waiter table assignments...")
        cursor.execute("""
            SELECT wta.*, t.table_number, w.name as waiter_name
            FROM waiter_table_assignments wta
            JOIN tables t ON wta.table_id = t.id
            JOIN waiters w ON wta.waiter_id = w.id
            LIMIT 10
        """)
        assignments = cursor.fetchall()
        print(f"Found {len(assignments)} table assignments:")
        for assignment in assignments:
            print(f"  - Table {assignment['table_number']} → {assignment['waiter_name']} (Waiter ID: {assignment['waiter_id']})")
        
        # Test 4: Check bills with tips
        print("\n[TEST 4] Checking bills with tips...")
        cursor.execute("""
            SELECT id, table_id, tip_amount, waiter_id, payment_status, paid_at
            FROM bills 
            WHERE tip_amount > 0 
            ORDER BY paid_at DESC 
            LIMIT 5
        """)
        bills_with_tips = cursor.fetchall()
        print(f"Found {len(bills_with_tips)} bills with tips:")
        for bill in bills_with_tips:
            print(f"  - Bill {bill['id']}: Table {bill['table_id']}, Tip ₹{bill['tip_amount']}, Waiter {bill['waiter_id']}, Status: {bill['payment_status']}")
        
        # Test 5: Check waiter_tips records
        if waiter_tips_exists:
            print("\n[TEST 5] Checking waiter_tips records...")
            cursor.execute("""
                SELECT wt.*, w.name as waiter_name
                FROM waiter_tips wt
                JOIN waiters w ON wt.waiter_id = w.id
                ORDER BY wt.created_at DESC
                LIMIT 5
            """)
            tip_records = cursor.fetchall()
            print(f"Found {len(tip_records)} tip records:")
            for tip in tip_records:
                print(f"  - {tip['waiter_name']} (ID: {tip['waiter_id']}): ₹{tip['tip_amount']} from Bill {tip['bill_id']}")
        
        # Test 6: Check hotel_modules tip visibility
        print("\n[TEST 6] Checking tip visibility settings...")
        cursor.execute("SELECT hotel_id, show_waiter_tips FROM hotel_modules")
        modules = cursor.fetchall()
        print(f"Found {len(modules)} hotel modules:")
        for module in modules:
            visibility = "Enabled" if module['show_waiter_tips'] else "Disabled"
            print(f"  - Hotel {module['hotel_id']}: Tips {visibility}")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        if not waiter_tips_exists:
            print("❌ waiter_tips table missing - restart the application to create it")
        if len(waiters) == 0:
            print("❌ No waiters found - create waiters in Manager Dashboard")
        if len(assignments) == 0:
            print("❌ No table assignments - assign waiters to tables in Manager Dashboard")
        if len(bills_with_tips) == 0:
            print("❌ No bills with tips - test by placing an order and adding a tip during payment")
        
        if waiter_tips_exists and len(waiters) > 0 and len(assignments) > 0:
            print("✅ Tip system appears to be set up correctly")
        
    except Exception as e:
        print(f"Error testing tip system: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tip_system()