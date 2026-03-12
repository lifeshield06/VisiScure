"""
Debug script to check waiter_calls table and verify data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_db_connection

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    print("=" * 80)
    print("WAITER CALLS DEBUG")
    print("=" * 80)
    
    # Check all waiter calls
    cursor.execute("""
        SELECT wc.*, t.table_number, w.name as waiter_name
        FROM waiter_calls wc
        JOIN tables t ON wc.table_id = t.id
        LEFT JOIN waiters w ON wc.waiter_id = w.id
        ORDER BY wc.created_at DESC
        LIMIT 10
    """)
    calls = cursor.fetchall()
    
    if calls:
        print(f"\nFound {len(calls)} waiter call(s):\n")
        for call in calls:
            print(f"ID: {call['id']}")
            print(f"  Table: {call['table_number']} (ID: {call['table_id']})")
            print(f"  Waiter: {call['waiter_name']} (ID: {call['waiter_id']})")
            print(f"  Guest: {call['guest_name'] or 'N/A'}")
            print(f"  Status: {call['status']}")
            print(f"  Created: {call['created_at']}")
            print(f"  Acknowledged: {call['acknowledged_at'] or 'N/A'}")
            print(f"  Completed: {call['completed_at'] or 'N/A'}")
            print("-" * 80)
    else:
        print("\n✗ No waiter calls found in database!")
        print("Try clicking the 'Call Waiter' button on the guest menu.")
    
    # Check pending calls for waiter 14 (Mahesh)
    print("\nPENDING CALLS FOR WAITER 14 (Mahesh Shinde):")
    cursor.execute("""
        SELECT wc.*, t.table_number
        FROM waiter_calls wc
        JOIN tables t ON wc.table_id = t.id
        WHERE wc.waiter_id = 14 AND wc.status = 'PENDING'
        ORDER BY wc.created_at DESC
    """)
    pending = cursor.fetchall()
    
    if pending:
        print(f"✓ Found {len(pending)} pending call(s):")
        for call in pending:
            print(f"  - Table {call['table_number']}: {call['guest_name'] or 'Guest'} ({call['created_at']})")
    else:
        print("✗ No pending calls for this waiter")
    
    # Check waiter session info
    print("\n" + "=" * 80)
    print("WAITER INFO:")
    cursor.execute("SELECT id, name, email FROM waiters WHERE id = 14")
    waiter = cursor.fetchone()
    if waiter:
        print(f"✓ Waiter found: {waiter['name']} ({waiter['email']})")
        print(f"  Login URL: http://localhost:5000/waiter/login")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
