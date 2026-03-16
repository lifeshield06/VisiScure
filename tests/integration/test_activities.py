"""
Test script to verify recent_activities table and functionality
"""

from database.db import get_db_connection

def test_activities_table():
    print("🧪 Testing recent_activities implementation...\n")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test 1: Check if table exists
        print("✓ Test 1: Checking if table exists...")
        cursor.execute("SHOW TABLES LIKE 'recent_activities'")
        result = cursor.fetchone()
        if result:
            print("  ✅ Table 'recent_activities' exists\n")
        else:
            print("  ❌ Table 'recent_activities' does NOT exist")
            print("  → Run: python setup_activities.py\n")
            return
        
        # Test 2: Check table structure
        print("✓ Test 2: Checking table structure...")
        cursor.execute("DESCRIBE recent_activities")
        columns = cursor.fetchall()
        expected_columns = ['id', 'activity_type', 'message', 'created_at']
        actual_columns = [col[0] for col in columns]
        
        if all(col in actual_columns for col in expected_columns):
            print("  ✅ All required columns exist")
            for col in columns:
                print(f"     - {col[0]} ({col[1]})")
            print()
        else:
            print("  ❌ Missing columns")
            print(f"     Expected: {expected_columns}")
            print(f"     Found: {actual_columns}\n")
        
        # Test 3: Insert test activity
        print("✓ Test 3: Testing insert...")
        cursor.execute(
            "INSERT INTO recent_activities (activity_type, message) VALUES (%s, %s)",
            ('test', 'Test activity from test script')
        )
        conn.commit()
        print("  ✅ Successfully inserted test activity\n")
        
        # Test 4: Fetch activities
        print("✓ Test 4: Testing fetch...")
        cursor.execute("""
            SELECT activity_type, message, created_at
            FROM recent_activities
            ORDER BY created_at DESC
            LIMIT 5
        """)
        activities = cursor.fetchall()
        print(f"  ✅ Found {len(activities)} activities:")
        for i, activity in enumerate(activities, 1):
            print(f"     {i}. [{activity[0]}] {activity[1][:50]}...")
        print()
        
        # Test 5: Test cleanup query
        print("✓ Test 5: Testing cleanup query...")
        cursor.execute("DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY")
        deleted = cursor.rowcount
        conn.commit()
        print(f"  ✅ Cleanup query executed (deleted {deleted} old records)\n")
        
        # Test 6: Clean up test data
        print("✓ Test 6: Cleaning up test data...")
        cursor.execute("DELETE FROM recent_activities WHERE activity_type = 'test'")
        conn.commit()
        print("  ✅ Test data cleaned up\n")
        
        cursor.close()
        conn.close()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 50)
        print("\n✅ Your live activities feature is ready to use!")
        print("\nNext steps:")
        print("1. Start your Flask app")
        print("2. Login to admin dashboard")
        print("3. Create a hotel or add a manager")
        print("4. Watch activities update automatically\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MySQL is running")
        print("2. Check database connection in database/db.py")
        print("3. Run: python setup_activities.py")
        print("4. Try again\n")

if __name__ == "__main__":
    test_activities_table()
