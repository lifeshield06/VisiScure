"""
Test complete session flow: Mark Paid → New Guest Scan → Fresh Session
"""
import sys
sys.path.insert(0, '.')

from database.db import get_db_connection
from orders.table_models import Bill, Table

print("=" * 70)
print("Testing Complete Session Flow")
print("=" * 70)

# Test with table 8 (from previous test)
table_id = 8

print(f"\n📋 STEP 1: Check current state of Table {table_id}")
print("-" * 70)

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

# Check table status
cursor.execute("SELECT * FROM tables WHERE id = %s", (table_id,))
table = cursor.fetchone()
print(f"Table Status: {table['status']}")
print(f"Session ID: {table.get('current_session_id', 'None')}")
print(f"Guest Name: {table.get('current_guest_name', 'None')}")

# Check for OPEN bills
cursor.execute("""
    SELECT bill_number, id, bill_status, payment_status, guest_name
    FROM bills 
    WHERE table_id = %s AND bill_status = 'OPEN'
""", (table_id,))
open_bills = cursor.fetchall()

print(f"\nOPEN Bills: {len(open_bills)}")
for bill in open_bills:
    print(f"  - {bill['bill_number']} | {bill['bill_status']} | {bill['payment_status']} | Guest: {bill.get('guest_name', 'N/A')}")

# Check for COMPLETED bills
cursor.execute("""
    SELECT bill_number, id, bill_status, payment_status, paid_at
    FROM bills 
    WHERE table_id = %s AND bill_status = 'COMPLETED'
    ORDER BY paid_at DESC LIMIT 3
""", (table_id,))
completed_bills = cursor.fetchall()

print(f"\nRecent COMPLETED Bills: {len(completed_bills)}")
for bill in completed_bills:
    print(f"  - {bill['bill_number']} | Paid at: {bill.get('paid_at', 'N/A')}")

# Check active_tables
cursor.execute("""
    SELECT * FROM active_tables 
    WHERE table_id = %s
    ORDER BY created_at DESC LIMIT 3
""", (table_id,))
active_entries = cursor.fetchall()

print(f"\nActive Tables Entries: {len(active_entries)}")
for entry in active_entries:
    print(f"  - Status: {entry['status']} | Created: {entry['created_at']} | Closed: {entry.get('closed_at', 'N/A')}")

print("\n" + "=" * 70)
print("📊 ANALYSIS")
print("=" * 70)

# Verify expected state
issues = []

if table['status'] != 'AVAILABLE':
    issues.append(f"❌ Table status is {table['status']}, expected AVAILABLE")
else:
    print("✅ Table status is AVAILABLE")

if table.get('current_session_id'):
    issues.append(f"❌ Session ID is {table['current_session_id']}, expected NULL")
else:
    print("✅ Session ID is NULL")

if table.get('current_guest_name'):
    issues.append(f"❌ Guest name is {table['current_guest_name']}, expected NULL")
else:
    print("✅ Guest name is NULL")

if len(open_bills) > 0:
    issues.append(f"❌ Found {len(open_bills)} OPEN bills, expected 0")
else:
    print("✅ No OPEN bills found")

# Check for ACTIVE entries in active_tables
active_count = sum(1 for e in active_entries if e['status'] == 'ACTIVE')
if active_count > 0:
    issues.append(f"❌ Found {active_count} ACTIVE entries in active_tables, expected 0")
else:
    print("✅ No ACTIVE entries in active_tables")

print("\n" + "=" * 70)
if issues:
    print("⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
    print("\n❌ Session cleanup is INCOMPLETE")
else:
    print("✅ ALL CHECKS PASSED!")
    print("✅ Table is ready for new guest")
    print("✅ New QR scan will start fresh session")

print("=" * 70)

cursor.close()
connection.close()
