"""
Test marking the actual bill as paid
"""
import sys
sys.path.insert(0, '.')

from orders.table_models import Bill, Table

print("=" * 60)
print("Testing Mark Paid on Actual Bill")
print("=" * 60)

bill_id = 12  # From check_bill_status.py

print(f"\n1. Testing Bill.complete_bill({bill_id})...")

try:
    result = Bill.complete_bill(bill_id)
    
    print(f"\n   Result: {result}")
    
    if result:
        print("   ✓ Bill marked as PAID successfully!")
        
        # Verify the changes
        print("\n2. Verifying changes...")
        bill = Bill.get_bill_by_id(bill_id)
        
        if bill:
            print(f"   Bill Status: {bill['bill_status']}")
            print(f"   Payment Status: {bill['payment_status']}")
            print(f"   Paid At: {bill.get('paid_at', 'Not set')}")
            
            # Check table status
            table = Table.get_table_by_id(bill['table_id'])
            if table:
                print(f"\n   Table Status: {table['status']}")
                print(f"   Session ID: {table.get('current_session_id', 'None')}")
                print(f"   Guest Name: {table.get('current_guest_name', 'None')}")
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS! Mark Paid is working correctly!")
        print("=" * 60)
    else:
        print("   ✗ Bill.complete_bill() returned False")
        print("   Check server logs for error details")
        
except Exception as e:
    print(f"\n   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
