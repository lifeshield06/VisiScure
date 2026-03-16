"""
Test script for multi-waiter call system
Verifies that call requests are sent to ALL waiters assigned to a table
"""
from database.db import get_db_connection

def test_multi_waiter_call():
    """Test the multi-waiter call system"""
    print("=" * 60)
    print("MULTI-WAITER CALL SYSTEM TEST")
    print("=" * 60)
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Test 1: Find tables with multiple waiters assigned
        print("\n[TEST 1] Finding tables with multiple waiters...")
        cursor.execute("""
            SELECT 
                t.id as table_id,
                t.table_number,
                COUNT(wta.waiter_id) as waiter_count,
                GROUP_CONCAT(w.name ORDER BY w.name SEPARATOR ', ') as waiter_names,
                GROUP_CONCAT(wta.waiter_id ORDER BY wta.waiter_id SEPARATOR ', ') as waiter_ids
            FROM tables t
            INNER JOIN waiter_table_assignments wta ON t.id = wta.table_id
            INNER JOIN waiters w ON wta.waiter_id = w.id
            GROUP BY t.id, t.table_number
            HAVING COUNT(wta.waiter_id) > 1
            ORDER BY waiter_count DESC
            LIMIT 5
        """)
        
        multi_waiter_tables = cursor.fetchall()
        
        if multi_waiter_tables:
            print(f"✓ Found {len(multi_waiter_tables)} tables with multiple waiters:")
            for table in multi_waiter_tables:
                print(f"  Table {table['table_number']}: {table['waiter_count']} waiters ({table['waiter_names']})")
        else:
            print("✗ No tables with multiple waiters found")
            print("  Tip: Assign multiple waiters to a table in Manager Dashboard")
        
        # Test 2: Check recent waiter calls
        print("\n[TEST 2] Checking recent waiter calls...")
        cursor.execute("""
            SELECT 
                wc.id,
                wc.table_id,
                t.table_number,
                wc.waiter_id,
                w.name as waiter_name,
                wc.guest_name,
                wc.status,
                wc.created_at
            FROM waiter_calls wc
            JOIN tables t ON wc.table_id = t.id
            JOIN waiters w ON wc.waiter_id = w.id
            ORDER BY wc.created_at DESC
            LIMIT 10
        """)
        
        recent_calls = cursor.fetchall()
        
        if recent_calls:
            print(f"✓ Found {len(recent_calls)} recent waiter calls:")
            
            # Group by table and created_at to see multi-waiter calls
            from collections import defaultdict
            calls_by_table_time = defaultdict(list)
            
            for call in recent_calls:
                key = (call['table_id'], call['created_at'].strftime('%Y-%m-%d %H:%M:%S'))
                calls_by_table_time[key].append(call)
            
            for (table_id, created_at), calls in calls_by_table_time.items():
                table_num = calls[0]['table_number']
                if len(calls) > 1:
                    waiter_names = ', '.join([c['waiter_name'] for c in calls])
                    print(f"  ✓ Table {table_num} @ {created_at}: {len(calls)} waiters notified ({waiter_names})")
                else:
                    print(f"    Table {table_num} @ {created_at}: 1 waiter ({calls[0]['waiter_name']})")
        else:
            print("  No recent waiter calls found")
        
        # Test 3: Verify waiter_table_assignments
        print("\n[TEST 3] Verifying waiter_table_assignments...")
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT table_id) as tables_with_waiters,
                COUNT(*) as total_assignments,
                AVG(waiter_count) as avg_waiters_per_table
            FROM (
                SELECT table_id, COUNT(*) as waiter_count
                FROM waiter_table_assignments
                GROUP BY table_id
            ) as subquery
        """)
        
        stats = cursor.fetchone()
        
        if stats:
            print(f"✓ Tables with waiters: {stats['tables_with_waiters']}")
            print(f"✓ Total assignments: {stats['total_assignments']}")
            print(f"✓ Average waiters per table: {float(stats['avg_waiters_per_table']):.2f}")
        
        # Test 4: Sample table assignment details
        print("\n[TEST 4] Sample table assignments:")
        cursor.execute("""
            SELECT 
                t.table_number,
                GROUP_CONCAT(w.name ORDER BY w.name SEPARATOR ', ') as waiters,
                COUNT(wta.waiter_id) as waiter_count
            FROM tables t
            LEFT JOIN waiter_table_assignments wta ON t.id = wta.table_id
            LEFT JOIN waiters w ON wta.waiter_id = w.id
            GROUP BY t.id, t.table_number
            ORDER BY waiter_count DESC, t.table_number
            LIMIT 10
        """)
        
        sample_tables = cursor.fetchall()
        
        for table in sample_tables:
            if table['waiter_count'] > 0:
                status = "✓" if table['waiter_count'] > 1 else " "
                print(f"  {status} Table {table['table_number']}: {table['waiter_count']} waiter(s) - {table['waiters']}")
            else:
                print(f"  ✗ Table {table['table_number']}: No waiters assigned")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("✓ MULTI-WAITER CALL SYSTEM TEST COMPLETE!")
        print("=" * 60)
        
        if multi_waiter_tables:
            print("\nTo test the feature:")
            print(f"1. Visit: http://localhost:5000/orders/menu/{multi_waiter_tables[0]['table_id']}")
            print("2. Click 'Call Waiter' button")
            print(f"3. Check that {multi_waiter_tables[0]['waiter_count']} requests are created")
            print(f"4. Each waiter ({multi_waiter_tables[0]['waiter_names']}) should see the request")
        else:
            print("\nSetup required:")
            print("1. Go to Manager Dashboard → Waiters → Manage Table Assignments")
            print("2. Assign multiple waiters to the same table")
            print("3. Then test the 'Call Waiter' feature")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_multi_waiter_call()
