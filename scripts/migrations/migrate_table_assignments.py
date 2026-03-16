"""
Migrate table assignments from tables.waiter_id to waiter_table_assignments
This ensures the mapping table has all the correct assignments
"""
from database.db import get_db_connection

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    print("=" * 60)
    print("MIGRATING TABLE ASSIGNMENTS")
    print("=" * 60)
    
    # Get all tables with waiter_id set
    cursor.execute("SELECT id, table_number, waiter_id FROM tables WHERE waiter_id IS NOT NULL")
    tables = cursor.fetchall()
    
    print(f"\nFound {len(tables)} tables with waiter_id set")
    
    migrated = 0
    skipped = 0
    
    for table in tables:
        table_id = table['id']
        waiter_id = table['waiter_id']
        table_number = table['table_number']
        
        # Check if assignment already exists
        cursor.execute(
            "SELECT * FROM waiter_table_assignments WHERE waiter_id = %s AND table_id = %s",
            (waiter_id, table_id)
        )
        
        if cursor.fetchone():
            print(f"  ✓ Table {table_number} (ID {table_id}) -> Waiter {waiter_id} [Already exists]")
            skipped += 1
        else:
            # Insert new assignment
            cursor.execute(
                "INSERT INTO waiter_table_assignments (waiter_id, table_id) VALUES (%s, %s)",
                (waiter_id, table_id)
            )
            print(f"  + Table {table_number} (ID {table_id}) -> Waiter {waiter_id} [MIGRATED]")
            migrated += 1
    
    connection.commit()
    
    print("\n" + "=" * 60)
    print(f"Migration complete!")
    print(f"  - Migrated: {migrated}")
    print(f"  - Skipped (already exists): {skipped}")
    print("=" * 60)
    
    # Show final state
    print("\nFinal waiter_table_assignments:")
    cursor.execute("""
        SELECT wta.*, t.table_number, w.name as waiter_name
        FROM waiter_table_assignments wta
        JOIN tables t ON wta.table_id = t.id
        JOIN waiters w ON wta.waiter_id = w.id
        ORDER BY w.name, t.table_number
    """)
    assignments = cursor.fetchall()
    
    for a in assignments:
        print(f"  - {a['waiter_name']} (ID {a['waiter_id']}) -> Table {a['table_number']} (ID {a['table_id']})")
    
    cursor.close()
    connection.close()
    
    print("\n✅ Migration successful! Restart Flask server to apply changes.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
