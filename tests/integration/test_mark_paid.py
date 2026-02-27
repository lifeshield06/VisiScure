"""
Test script to verify Mark Paid functionality
"""
from database.db import get_db_connection
from orders.table_models import Bill

def test_mark_paid():
    """Test the complete_bill method"""
    print("=" * 60)
    print("Testing Mark Paid Functionality")
    print("=" * 60)
    
    try:
        # Get an open bill
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, bill_number, table_id, bill_status, payment_status 
            FROM bills 
            WHERE bill_status = 'OPEN' AND payment_status = 'PENDING'
            LIMIT 1
        """)
        
        bill = cursor.fetchone()
        
        if not bill:
            print("❌ No open bills found to test")
            print("\nCreate a test bill first by:")
            print("1. Scanning a table QR code")
            print("2. Placing an order as a guest")
            cursor.close()
            connection.close()
            return
        
        print(f"\n✓ Found test bill:")
        print(f"  Bill ID: {bill['id']}")
        print(f"  Bill Number: {bill['bill_number']}")
        print(f"  Table ID: {bill['table_id']}")
        print(f"  Bill Status: {bill['bill_status']}")
        print(f"  Payment Status: {bill['payment_status']}")
        
        # Get table status before
        cursor.execute("SELECT status, current_session_id, current_guest_name FROM tables WHERE id = %s", (bill['table_id'],))
        table_before = cursor.fetchone()
        print(f"\n✓ Table status BEFORE:")
        print(f"  Status: {table_before['status']}")
        print(f"  Session ID: {table_before['current_session_id']}")
        print(f"  Guest Name: {table_before['current_guest_name']}")
        
        cursor.close()
        connection.close()
        
        # Test complete_bill method
        print(f"\n⏳ Testing Bill.complete_bill({bill['id']})...")
        result = Bill.complete_bill(bill['id'])
        
        if result:
            print("✅ Bill.complete_bill() returned True")
            
            # Verify changes
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Check bill status
            cursor.execute("SELECT bill_status, payment_status, paid_at FROM bills WHERE id = %s", (bill['id'],))
            bill_after = cursor.fetchone()
            print(f"\n✓ Bill status AFTER:")
            print(f"  Bill Status: {bill_after['bill_status']}")
            print(f"  Payment Status: {bill_after['payment_status']}")
            print(f"  Paid At: {bill_after['paid_at']}")
            
            # Check table status
            cursor.execute("SELECT status, current_session_id, current_guest_name FROM tables WHERE id = %s", (bill['table_id'],))
            table_after = cursor.fetchone()
            print(f"\n✓ Table status AFTER:")
            print(f"  Status: {table_after['status']}")
            print(f"  Session ID: {table_after['current_session_id']}")
            print(f"  Guest Name: {table_after['current_guest_name']}")
            
            # Check active_tables
            cursor.execute("SELECT status, closed_at FROM active_tables WHERE table_id = %s ORDER BY id DESC LIMIT 1", (bill['table_id'],))
            active_table = cursor.fetchone()
            if active_table:
                print(f"\n✓ Active Tables Entry:")
                print(f"  Status: {active_table['status']}")
                print(f"  Closed At: {active_table['closed_at']}")
            
            cursor.close()
            connection.close()
            
            # Verify expectations
            print("\n" + "=" * 60)
            print("Verification:")
            print("=" * 60)
            
            checks = [
                (bill_after['bill_status'] == 'COMPLETED', "Bill status is COMPLETED"),
                (bill_after['payment_status'] == 'PAID', "Payment status is PAID"),
                (bill_after['paid_at'] is not None, "Paid timestamp is set"),
                (table_after['status'] == 'AVAILABLE', "Table status is AVAILABLE"),
                (table_after['current_session_id'] is None, "Session ID is cleared"),
                (table_after['current_guest_name'] is None, "Guest name is cleared"),
            ]
            
            all_passed = True
            for passed, description in checks:
                status = "✅" if passed else "❌"
                print(f"{status} {description}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print("\n🎉 All checks passed! Mark Paid is working correctly!")
            else:
                print("\n⚠️  Some checks failed. Review the output above.")
        else:
            print("❌ Bill.complete_bill() returned False")
            print("Check the server logs for error details")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mark_paid()
