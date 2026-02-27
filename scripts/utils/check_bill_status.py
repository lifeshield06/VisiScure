"""
Check the status of the bill shown in the Active Bills page
"""
import sys
sys.path.insert(0, '.')

from database.db import get_db_connection

print("=" * 60)
print("Checking Bill Status")
print("=" * 60)

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    # Get the bill from the screenshot: BILL-20260225102802-910
    bill_number = "BILL-20260225102802-910"
    
    cursor.execute("""
        SELECT b.*, t.table_number, t.status as table_status
        FROM bills b
        JOIN tables t ON b.table_id = t.id
        WHERE b.bill_number = %s
    """, (bill_number,))
    
    bill = cursor.fetchone()
    
    if bill:
        print(f"\n✓ Found bill: {bill_number}")
        print(f"  Bill ID: {bill['id']}")
        print(f"  Table ID: {bill['table_id']}")
        print(f"  Table Number: {bill['table_number']}")
        print(f"  Guest: {bill.get('guest_name', 'N/A')}")
        print(f"  Total Amount: ₹{bill['total_amount']}")
        print(f"  Bill Status: {bill['bill_status']}")
        print(f"  Payment Status: {bill['payment_status']}")
        print(f"  Table Status: {bill['table_status']}")
        print(f"  Created: {bill['created_at']}")
        
        if bill['bill_status'] == 'OPEN' and bill['payment_status'] == 'PENDING':
            print("\n✓ Bill is ready to be marked as PAID")
            print(f"\nTo test, call: Bill.complete_bill({bill['id']})")
        else:
            print(f"\n⚠ Bill status: {bill['bill_status']}, Payment: {bill['payment_status']}")
            print("  This bill may have already been processed")
    else:
        print(f"\n✗ Bill not found: {bill_number}")
        print("\nSearching for any OPEN bills...")
        
        cursor.execute("""
            SELECT b.bill_number, b.id, b.table_id, t.table_number, b.total_amount, 
                   b.bill_status, b.payment_status
            FROM bills b
            JOIN tables t ON b.table_id = t.id
            WHERE b.bill_status = 'OPEN'
            ORDER BY b.created_at DESC
            LIMIT 5
        """)
        
        open_bills = cursor.fetchall()
        
        if open_bills:
            print(f"\nFound {len(open_bills)} OPEN bills:")
            for bill in open_bills:
                print(f"  - {bill['bill_number']} | Table {bill['table_number']} | ₹{bill['total_amount']} | {bill['payment_status']}")
        else:
            print("\n✗ No OPEN bills found in database")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
