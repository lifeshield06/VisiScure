"""Check waiter_table_assignments table data"""
from database.db import get_db_connection

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    # Check waiter_table_assignments table
    print("=" * 60)
    print("WAITER_TABLE_ASSIGNMENTS TABLE")
    print("=" * 60)
    cursor.execute("SELECT * FROM waiter_table_assignments ORDER BY waiter_id, table_id")
    assignments = cursor.fetchall()
    
    if assignments:
        print(f"Found {len(assignments)} assignments:")
        for a in assignments:
            print(f"  - Waiter ID {a['waiter_id']} -> Table ID {a['table_id']}")
    else:
        print("⚠️  NO ASSIGNMENTS FOUND IN waiter_table_assignments TABLE!")
        print("This is why waiters see no tables!")
    
    print("\n" + "=" * 60)
    print("TABLES WITH waiter_id COLUMN (OLD METHOD)")
    print("=" * 60)
    cursor.execute("SELECT id, table_number, waiter_id FROM tables WHERE waiter_id IS NOT NULL ORDER BY table_number")
    tables = cursor.fetchall()
    
    if tables:
        print(f"Found {len(tables)} tables with waiter_id set:")
        for t in tables:
            print(f"  - Table {t['table_number']} (ID {t['id']}) -> Waiter ID {t['waiter_id']}")
    else:
        print("No tables have waiter_id set")
    
    print("\n" + "=" * 60)
    print("SOLUTION")
    print("=" * 60)
    print("If waiter_table_assignments is empty but tables.waiter_id has data,")
    print("we need to migrate the data from tables.waiter_id to waiter_table_assignments")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"Error: {e}")
