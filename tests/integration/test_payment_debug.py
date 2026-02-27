#!/usr/bin/env python
"""Debug script to test payment functionality"""

import sys
sys.path.insert(0, '.')

from database.db import get_db_connection
from orders.table_models import Bill, Table

def test_database_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check open bills
        cursor.execute('SELECT COUNT(*) as count FROM bills WHERE bill_status = "OPEN"')
        result = cursor.fetchone()
        print(f"✓ Database connection: OK")
        print(f"✓ Open bills in database: {result['count']}")
        
        # Check if tip_amount column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'bills' 
            AND COLUMN_NAME = 'tip_amount'
        """)
        tip_col = cursor.fetchone()
        if tip_col:
            print(f"✓ tip_amount column exists in bills table")
        else:
            print(f"✗ tip_amount column MISSING in bills table")
        
        # Get a sample open bill
        cursor.execute('SELECT * FROM bills WHERE bill_status = "OPEN" LIMIT 1')
        bill = cursor.fetchone()
        if bill:
            print(f"\n✓ Sample open bill found:")
            print(f"  - Bill ID: {bill['id']}")
            print(f"  - Bill Number: {bill.get('bill_number')}")
            print(f"  - Table ID: {bill['table_id']}")
            print(f"  - Subtotal: ₹{bill.get('subtotal', 0)}")
            print(f"  - Tax: ₹{bill.get('tax_amount', 0)}")
            print(f"  - Total: ₹{bill.get('total_amount', 0)}")
            print(f"  - Status: {bill.get('bill_status')}")
        else:
            print(f"\n⚠ No open bills found - create an order first")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_payment_method():
    """Test the payment method directly"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Find an open bill
        cursor.execute('SELECT * FROM bills WHERE bill_status = "OPEN" LIMIT 1')
        bill = cursor.fetchone()
        
        if not bill:
            print("\n⚠ Cannot test payment - no open bills found")
            print("  Please create an order first through the QR menu")
            cursor.close()
            conn.close()
            return False
        
        bill_id = bill['id']
        table_id = bill['table_id']
        
        print(f"\n🧪 Testing payment for Bill ID: {bill_id}, Table ID: {table_id}")
        
        cursor.close()
        conn.close()
        
        # Test the payment method
        result = Bill.process_payment_atomic(table_id, bill_id, 'CASH', 50.00)
        
        if result:
            print(f"✓ Payment processed successfully!")
            print(f"  Check the server logs for detailed output")
        else:
            print(f"✗ Payment failed!")
            print(f"  Check the server logs for error details")
        
        return result
        
    except Exception as e:
        print(f"✗ Payment test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("PAYMENT DEBUG SCRIPT")
    print("=" * 60)
    
    print("\n1. Testing database connection...")
    db_ok = test_database_connection()
    
    if db_ok:
        print("\n2. Testing payment method...")
        payment_ok = test_payment_method()
        
        if payment_ok:
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("✗ PAYMENT TEST FAILED")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ DATABASE CONNECTION FAILED")
        print("=" * 60)
