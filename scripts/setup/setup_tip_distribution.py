"""
Setup script for tip distribution system
1. Creates waiter_tips table
2. Migrates existing tips from bills table
"""
from database.db import get_db_connection

def setup_tip_distribution():
    """Complete setup for tip distribution system"""
    print("=" * 60)
    print("TIP DISTRIBUTION SYSTEM SETUP")
    print("=" * 60)
    
    # Step 1: Create waiter_tips table
    print("\n[STEP 1] Creating waiter_tips table...")
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiter_tips (
                id INT AUTO_INCREMENT PRIMARY KEY,
                waiter_id INT NOT NULL,
                bill_id INT NOT NULL,
                tip_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                INDEX idx_waiter_id (waiter_id),
                INDEX idx_bill_id (bill_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        connection.commit()
        print("✓ waiter_tips table created successfully!")
        
        # Verify table structure
        cursor.execute("DESCRIBE waiter_tips")
        columns = cursor.fetchall()
        
        print("\nTable structure:")
        for col in columns:
            print(f"  {col}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"✗ Error creating waiter_tips table: {e}")
        return False
    
    # Step 2: Migrate existing tips
    print("\n[STEP 2] Migrating existing tips...")
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
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
        else:
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
        print(f"✗ Error migrating tips: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ TIP DISTRIBUTION SYSTEM SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. Test tip distribution by creating a new order and adding a tip")
    print("3. Check the waiter tip summary in the manager dashboard")
    
    return True

if __name__ == "__main__":
    setup_tip_distribution()
