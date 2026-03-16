"""
End-to-End Test: Complete flow from order to payment to new guest
"""
import sys
sys.path.insert(0, '.')

from database.db import get_db_connection
from orders.table_models import Bill, Table, TableOrder

print("=" * 70)
print("END-TO-END SESSION FLOW TEST")
print("=" * 70)

table_id = 8  # Using table 8 for testing

# ============================================================================
# SCENARIO 1: Check initial state (should be clean from previous test)
# ============================================================================
print("\n📋 SCENARIO 1: Verify Table is Clean")
print("-" * 70)

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

cursor.execute("SELECT * FROM tables WHERE id = %s", (table_id,))
table = cursor.fetchone()

cursor.execute("""
    SELECT COUNT(*) as count FROM bills 
    WHERE table_id = %s AND bill_status = 'OPEN'
""", (table_id,))
open_count = cursor.fetchone()['count']

print(f"Table Status: {table['status']}")
print(f"OPEN Bills: {open_count}")

if table['status'] == 'AVAILABLE' and open_count == 0:
    print("✅ Table is clean and ready")
else:
    print("❌ Table is not clean - test cannot proceed")
    cursor.close()
    connection.close()
    sys.exit(1)

# ============================================================================
# SCENARIO 2: Simulate new guest scanning QR
# ============================================================================
print("\n📋 SCENARIO 2: New Guest Scans QR")
print("-" * 70)

# Check what the system would return
open_bill = Bill.get_any_open_bill_for_table(table_id)

if open_bill:
    print(f"❌ FAIL: Found OPEN bill {open_bill['bill_number']}")
    print("   System would show old bill to new guest!")
    cursor.close()
    connection.close()
    sys.exit(1)
else:
    print("✅ No OPEN bill found")
    print("✅ System will allow new guest to order")

# ============================================================================
# SCENARIO 3: Simulate guest placing order
# ============================================================================
print("\n📋 SCENARIO 3: Guest Places Order")
print("-" * 70)

guest_name = "Test Guest"
session_id = f"session_test_{table_id}"
items = [
    {"name": "Test Dish", "price": 100.00, "quantity": 1}
]
subtotal = 100.00

# Get hotel_id from table
cursor.execute("SELECT hotel_id FROM tables WHERE id = %s", (table_id,))
hotel_id = cursor.fetchone()['hotel_id']

# Create order
order_id, error = TableOrder.add_order(
    table_id=table_id,
    session_id=session_id,
    items=items,
    total_amount=subtotal,
    hotel_id=hotel_id,
    guest_name=guest_name
)

if order_id:
    print(f"✅ Order created: ID {order_id}")
    
    # Create bill
    bill_result = Bill.create_bill(
        order_id=order_id,
        table_id=table_id,
        session_id=session_id,
        items=items,
        subtotal=subtotal,
        hotel_id=hotel_id,
        guest_name=guest_name
    )
    
    if bill_result:
        bill_id = bill_result['bill_id']
        bill_number = bill_result['bill_number']
        print(f"✅ Bill created: {bill_number} (ID: {bill_id})")
    else:
        print("❌ Failed to create bill")
        cursor.close()
        connection.close()
        sys.exit(1)
else:
    print(f"❌ Failed to create order: {error}")
    cursor.close()
    connection.close()
    sys.exit(1)

# ============================================================================
# SCENARIO 4: Verify bill is OPEN
# ============================================================================
print("\n📋 SCENARIO 4: Verify Bill is OPEN")
print("-" * 70)

# Get fresh connection
connection2 = get_db_connection()
cursor2 = connection2.cursor(dictionary=True)

cursor2.execute("""
    SELECT bill_number, bill_status, payment_status 
    FROM bills WHERE id = %s
""", (bill_id,))
bill_check = cursor2.fetchone()

print(f"Bill: {bill_check['bill_number']}")
print(f"Bill Status: {bill_check['bill_status']}")
print(f"Payment Status: {bill_check['payment_status']}")

if bill_check['bill_status'] == 'OPEN' and bill_check['payment_status'] == 'PENDING':
    print("✅ Bill is OPEN and PENDING")
else:
    print("❌ Bill status is incorrect")
    cursor2.close()
    connection2.close()
    cursor.close()
    connection.close()
    sys.exit(1)

cursor2.close()
connection2.close()

# ============================================================================
# SCENARIO 5: Manager marks bill as PAID
# ============================================================================
print("\n📋 SCENARIO 5: Manager Marks Bill as PAID")
print("-" * 70)

result = Bill.complete_bill(bill_id)

if result:
    print("✅ Bill marked as PAID successfully")
else:
    print("❌ Failed to mark bill as PAID")
    cursor.close()
    connection.close()
    sys.exit(1)

# ============================================================================
# SCENARIO 6: Verify table is clean again
# ============================================================================
print("\n📋 SCENARIO 6: Verify Table is Clean Again")
print("-" * 70)

# Get fresh connection
connection3 = get_db_connection()
cursor3 = connection3.cursor(dictionary=True)

cursor3.execute("SELECT * FROM tables WHERE id = %s", (table_id,))
table_after = cursor3.fetchone()

cursor3.execute("""
    SELECT COUNT(*) as count FROM bills 
    WHERE table_id = %s AND bill_status = 'OPEN'
""", (table_id,))
open_count_after = cursor3.fetchone()['count']

cursor3.execute("""
    SELECT bill_status, payment_status, paid_at 
    FROM bills WHERE id = %s
""", (bill_id,))
bill_after = cursor3.fetchone()

print(f"Table Status: {table_after['status']}")
print(f"Session ID: {table_after.get('current_session_id', 'NULL')}")
print(f"Guest Name: {table_after.get('current_guest_name', 'NULL')}")
print(f"OPEN Bills: {open_count_after}")
print(f"Bill Status: {bill_after['bill_status']}")
print(f"Payment Status: {bill_after['payment_status']}")
print(f"Paid At: {bill_after.get('paid_at', 'NULL')}")

all_good = True
if table_after['status'] != 'AVAILABLE':
    print("❌ Table status is not AVAILABLE")
    all_good = False
else:
    print("✅ Table status is AVAILABLE")

if table_after.get('current_session_id'):
    print("❌ Session ID is not NULL")
    all_good = False
else:
    print("✅ Session ID is NULL")

if table_after.get('current_guest_name'):
    print("❌ Guest name is not NULL")
    all_good = False
else:
    print("✅ Guest name is NULL")

if open_count_after > 0:
    print(f"❌ Found {open_count_after} OPEN bills")
    all_good = False
else:
    print("✅ No OPEN bills")

if bill_after['bill_status'] != 'COMPLETED':
    print("❌ Bill status is not COMPLETED")
    all_good = False
else:
    print("✅ Bill status is COMPLETED")

if bill_after['payment_status'] != 'PAID':
    print("❌ Payment status is not PAID")
    all_good = False
else:
    print("✅ Payment status is PAID")

# ============================================================================
# SCENARIO 7: New guest scans QR (should see clean table)
# ============================================================================
print("\n📋 SCENARIO 7: New Guest Scans QR Again")
print("-" * 70)

open_bill_check = Bill.get_any_open_bill_for_table(table_id)

if open_bill_check:
    print(f"❌ FAIL: Found OPEN bill {open_bill_check['bill_number']}")
    print("   New guest would see old bill!")
    all_good = False
else:
    print("✅ No OPEN bill found")
    print("✅ New guest will see clean table")

# ============================================================================
# FINAL RESULT
# ============================================================================
print("\n" + "=" * 70)
if all_good:
    print("🎉 ALL TESTS PASSED!")
    print("✅ Session flow is working correctly")
    print("✅ Old bills do not appear for new guests")
    print("✅ Tables are properly cleaned after payment")
else:
    print("❌ SOME TESTS FAILED")
    print("⚠️  Session flow has issues")

print("=" * 70)

cursor.close()
connection.close()
cursor3.close()
connection3.close()
