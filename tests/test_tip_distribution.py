"""
Test script for tip distribution system
Verifies that tips are distributed correctly among assigned waiters
"""
from database.db import get_db_connection

def test_tip_distribution():
    """Test the tip distribution system"""
    print("=" * 60)
    print("TIP DISTRIBUTION SYSTEM TEST")
    print("=" * 60)
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Test 1: Check waiter_tips table exists
        print("\n[TEST 1] Checking waiter_tips table...")
        cursor.execute("SHOW TABLES LIKE 'waiter_tips'")
        result = cursor.fetchone()
        
        if result:
            print("✓ waiter_tips table exists")
        else:
            print("✗ waiter_tips table NOT FOUND")
            print("  Run: python setup_tip_distribution.py")
            return False
        
        # Test 2: Check table structure
        print("\n[TEST 2] Verifying table structure...")
        cursor.execute("DESCRIBE waiter_tips")
        columns = cursor.fetchall()
        
        required_columns = ['id', 'waiter_id', 'bill_id', 'tip_amount', 'created_at']
        found_columns = [col['Field'] for col in columns]
        
        all_present = all(col in found_columns for col in required_columns)
        
        if all_present:
            print("✓ All required columns present")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
        else:
            print("✗ Missing columns")
            missing = [col for col in required_columns if col not in found_columns]
            print(f"  Missing: {missing}")
            return False
        
        # Test 3: Check for existing tip records
        print("\n[TEST 3] Checking existing tip records...")
        cursor.execute("SELECT COUNT(*) as count FROM waiter_tips")
        result = cursor.fetchone()
        tip_count = result['count']
        
        print(f"✓ Found {tip_count} tip records in waiter_tips table")
        
        # Test 4: Sample tip distribution data
        if tip_count > 0:
            print("\n[TEST 4] Sample tip distribution data...")
            cursor.execute("""
                SELECT 
                    wt.id,
                    wt.bill_id,
                    w.name as waiter_name,
                    wt.tip_amount,
                    wt.created_at,
                    b.table_id,
                    t.table_number
                FROM waiter_tips wt
                JOIN waiters w ON wt.waiter_id = w.id
                JOIN bills b ON wt.bill_id = b.id
                JOIN tables t ON b.table_id = t.id
                ORDER BY wt.created_at DESC
                LIMIT 5
            """)
            
            samples = cursor.fetchall()
            
            print(f"Latest {len(samples)} tip records:")
            for sample in samples:
                print(f"  Bill #{sample['bill_id']} | Table {sample['table_number']} | "
                      f"{sample['waiter_name']} | ₹{sample['tip_amount']:.2f} | "
                      f"{sample['created_at']}")
        
        # Test 5: Verify tip distribution logic
        print("\n[TEST 5] Verifying tip distribution logic...")
        cursor.execute("""
            SELECT 
                b.id as bill_id,
                b.table_id,
                t.table_number,
                b.tip_amount as total_tip,
                COUNT(wt.id) as waiter_count,
                SUM(wt.tip_amount) as distributed_tip
            FROM bills b
            JOIN tables t ON b.table_id = t.id
            LEFT JOIN waiter_tips wt ON b.id = wt.bill_id
            WHERE b.payment_status = 'PAID' 
            AND b.tip_amount > 0
            GROUP BY b.id, b.table_id, t.table_number, b.tip_amount
            HAVING COUNT(wt.id) > 0
            ORDER BY b.paid_at DESC
            LIMIT 5
        """)
        
        bills = cursor.fetchall()
        
        if bills:
            print(f"Checking {len(bills)} recent bills with tips:")
            all_correct = True
            
            for bill in bills:
                total_tip = float(bill['total_tip'])
                distributed_tip = float(bill['distributed_tip'])
                waiter_count = bill['waiter_count']
                
                # Allow small rounding differences (0.01)
                is_correct = abs(total_tip - distributed_tip) < 0.02
                
                status = "✓" if is_correct else "✗"
                print(f"  {status} Bill #{bill['bill_id']} | Table {bill['table_number']} | "
                      f"Total: ₹{total_tip:.2f} | Distributed: ₹{distributed_tip:.2f} | "
                      f"Waiters: {waiter_count}")
                
                if not is_correct:
                    all_correct = False
            
            if all_correct:
                print("\n✓ All tip distributions are correct!")
            else:
                print("\n✗ Some tip distributions have discrepancies")
        else:
            print("  No bills with distributed tips found")
        
        # Test 6: Check waiter tip summary
        print("\n[TEST 6] Testing waiter tip summary...")
        cursor.execute("""
            SELECT 
                w.id as waiter_id,
                w.name as waiter_name,
                SUM(CASE WHEN DATE(wt.created_at) = CURDATE() THEN wt.tip_amount ELSE 0 END) as today_tip,
                SUM(wt.tip_amount) as total_tip,
                COUNT(DISTINCT wt.bill_id) as total_bills
            FROM waiter_tips wt
            JOIN waiters w ON wt.waiter_id = w.id
            WHERE wt.tip_amount > 0
            GROUP BY w.id, w.name
            ORDER BY total_tip DESC
            LIMIT 5
        """)
        
        waiter_tips = cursor.fetchall()
        
        if waiter_tips:
            print(f"Top {len(waiter_tips)} waiters by tips:")
            for wt in waiter_tips:
                print(f"  {wt['waiter_name']}: Today ₹{float(wt['today_tip']):.2f} | "
                      f"Total ₹{float(wt['total_tip']):.2f} | Bills: {wt['total_bills']}")
        else:
            print("  No waiter tips found")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("✓ TIP DISTRIBUTION SYSTEM TEST COMPLETE!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_tip_distribution()
