"""
Migrate existing tips from bills table to waiter_tips table
This ensures backward compatibility with existing bills that have tips
"""
from database.db import get_db_connection

def migrate_existing_tips():
    """Migrate tips from bills.tip_amount to waiter_tips table"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        print("Migrating existing tips to waiter_tips table...")
        
        # Find all paid bills with tips that don't have waiter_tips entries yet
        cursor.execute("""
            SELECT b.id as bill_id, b.table_id, b.tip_amount, b.paid_at, b.waiter_id
            FROM bills b
            WHERE b.payment_status = 'PAID' 
            AND b.tip_amount > 0
            AND NOT EXISTS (
                SELECT 1 FROM waiter_tips wt WHERE wt.bill_id = b.id
            )
            ORDER BY b.paid_at DESC
        """)
        
        bills_with_tips = cursor.fetchall()
        
        if not bills_with_tips:
            print("✓ No bills to migrate. All tips are already in waiter_tips table.")
            cursor.close()
            connection.close()
            return
        
        print(f"Found {len(bills_with_tips)} bills with tips to migrate")
        
        migrated_count = 0
        skipped_count = 0
        
        for bill in bills_with_tips:
            bill_id = bill['bill_id']
            table_id = bill['table_id']
            tip_amount = float(bill['tip_amount'])
            paid_at = bill['paid_at']
            old_waiter_id = bill.get('waiter_id')
            
            # Get all waiters assigned to this table
            cursor.execute("""
                SELECT DISTINCT waiter_id 
                FROM waiter_table_assignments 
                WHERE table_id = %s
            """, (table_id,))
            
            assigned_waiters = cursor.fetchall()
            
            if assigned_waiters and len(assigned_waiters) > 0:
                waiter_count = len(assigned_waiters)
                tip_per_waiter = round(tip_amount / waiter_count, 2)
                
                print(f"  Bill {bill_id}: Distributing ₹{tip_amount} among {waiter_count} waiters (₹{tip_per_waiter} each)")
                
                # Insert tip records for each waiter
                for waiter in assigned_waiters:
                    waiter_id = waiter['waiter_id']
                    cursor.execute("""
                        INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, created_at)
                        VALUES (%s, %s, %s, %s)
                    """, (waiter_id, bill_id, tip_per_waiter, paid_at))
                
                migrated_count += 1
                
            elif old_waiter_id:
                # Fallback: Use old waiter_id from bills table if no assignments found
                print(f"  Bill {bill_id}: No table assignments found, using bill.waiter_id={old_waiter_id}")
                cursor.execute("""
                    INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (old_waiter_id, bill_id, tip_amount, paid_at))
                
                migrated_count += 1
            else:
                print(f"  Bill {bill_id}: SKIPPED - No waiters assigned to table {table_id}")
                skipped_count += 1
        
        connection.commit()
        
        print(f"\n✓ Migration complete!")
        print(f"  Migrated: {migrated_count} bills")
        print(f"  Skipped: {skipped_count} bills (no waiter assignments)")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) as count FROM waiter_tips")
        result = cursor.fetchone()
        total_tip_records = result['count']
        
        print(f"\nTotal waiter_tips records: {total_tip_records}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error migrating tips: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_existing_tips()
