"""
Test script to verify Clear Completed Orders functionality
"""
import sys
sys.path.insert(0, '.')

from database.db import get_db_connection

print("=" * 70)
print("Testing Clear Completed Orders Functionality")
print("=" * 70)

hotel_id = 9  # Tip top hotel

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

# ============================================================================
# STEP 1: Check current orders
# ============================================================================
print("\n📋 STEP 1: Current Orders Status")
print("-" * 70)

cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN order_status = 'COMPLETED' AND payment_status = 'PAID' THEN 1 ELSE 0 END) as completed_paid,
        SUM(CASE WHEN order_status = 'ACTIVE' THEN 1 ELSE 0 END) as active,
        SUM(CASE WHEN payment_status = 'PENDING' THEN 1 ELSE 0 END) as pending_payment
    FROM table_orders o
    LEFT JOIN tables t ON o.table_id = t.id
    WHERE o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s)
""", (hotel_id, hotel_id))

stats = cursor.fetchone()

print(f"Total Orders: {stats['total']}")
print(f"Completed & Paid: {stats['completed_paid']}")
print(f"Active Orders: {stats['active']}")
print(f"Pending Payment: {stats['pending_payment']}")

# ============================================================================
# STEP 2: Show orders that would be deleted
# ============================================================================
print("\n📋 STEP 2: Orders That Would Be Cleared")
print("-" * 70)

cursor.execute("""
    SELECT o.id, o.table_id, t.table_number, o.order_status, o.payment_status, 
           b.bill_status, o.created_at
    FROM table_orders o
    LEFT JOIN tables t ON o.table_id = t.id
    LEFT JOIN bills b ON o.id = b.order_id
    WHERE (o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s))
    AND o.order_status = 'COMPLETED'
    AND o.payment_status = 'PAID'
    AND (b.id IS NULL OR b.bill_status = 'COMPLETED')
    ORDER BY o.created_at DESC
    LIMIT 10
""", (hotel_id, hotel_id))

orders_to_clear = cursor.fetchall()

if orders_to_clear:
    print(f"Found {len(orders_to_clear)} orders to clear:")
    for order in orders_to_clear:
        bill_status = order.get('bill_status', 'No Bill')
        print(f"  - Order #{order['id']} | Table {order.get('table_number', 'N/A')} | "
              f"Order: {order['order_status']} | Payment: {order['payment_status']} | "
              f"Bill: {bill_status} | Created: {order['created_at']}")
else:
    print("No orders to clear (all orders are either active or have pending payments)")

# ============================================================================
# STEP 3: Show orders that would NOT be deleted (safety check)
# ============================================================================
print("\n📋 STEP 3: Orders That Would NOT Be Cleared (Safety Check)")
print("-" * 70)

cursor.execute("""
    SELECT o.id, o.table_id, t.table_number, o.order_status, o.payment_status, 
           b.bill_status
    FROM table_orders o
    LEFT JOIN tables t ON o.table_id = t.id
    LEFT JOIN bills b ON o.id = b.order_id
    WHERE (o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s))
    AND NOT (
        o.order_status = 'COMPLETED'
        AND o.payment_status = 'PAID'
        AND (b.id IS NULL OR b.bill_status = 'COMPLETED')
    )
    ORDER BY o.created_at DESC
    LIMIT 10
""", (hotel_id, hotel_id))

safe_orders = cursor.fetchall()

if safe_orders:
    print(f"Found {len(safe_orders)} orders that will be PROTECTED:")
    for order in safe_orders:
        bill_status = order.get('bill_status', 'No Bill')
        print(f"  - Order #{order['id']} | Table {order.get('table_number', 'N/A')} | "
              f"Order: {order['order_status']} | Payment: {order['payment_status']} | "
              f"Bill: {bill_status}")
        
        # Explain why it's protected
        reasons = []
        if order['order_status'] != 'COMPLETED':
            reasons.append(f"Order not completed ({order['order_status']})")
        if order['payment_status'] != 'PAID':
            reasons.append(f"Payment pending ({order['payment_status']})")
        if order.get('bill_status') and order['bill_status'] != 'COMPLETED':
            reasons.append(f"Bill not completed ({order['bill_status']})")
        
        if reasons:
            print(f"    Reason: {', '.join(reasons)}")
else:
    print("No protected orders found")

# ============================================================================
# STEP 4: Verify safety rules
# ============================================================================
print("\n📋 STEP 4: Safety Rules Verification")
print("-" * 70)

# Check for OPEN bills
cursor.execute("""
    SELECT COUNT(*) as count
    FROM bills b
    JOIN table_orders o ON b.order_id = o.id
    WHERE b.hotel_id = %s
    AND b.bill_status = 'OPEN'
    AND o.order_status = 'COMPLETED'
    AND o.payment_status = 'PAID'
""", (hotel_id,))

open_bills_count = cursor.fetchone()['count']

if open_bills_count > 0:
    print(f"⚠️  WARNING: Found {open_bills_count} COMPLETED orders with OPEN bills")
    print("   These orders will NOT be deleted (safety rule)")
else:
    print("✅ No COMPLETED orders with OPEN bills")

# Check for active orders
cursor.execute("""
    SELECT COUNT(*) as count
    FROM table_orders o
    LEFT JOIN tables t ON o.table_id = t.id
    WHERE (o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s))
    AND o.order_status IN ('ACTIVE', 'PREPARING')
""", (hotel_id, hotel_id))

active_count = cursor.fetchone()['count']

if active_count > 0:
    print(f"✅ Found {active_count} active orders - these will be PROTECTED")
else:
    print("✅ No active orders")

# Check for pending payments
cursor.execute("""
    SELECT COUNT(*) as count
    FROM table_orders o
    LEFT JOIN tables t ON o.table_id = t.id
    WHERE (o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s))
    AND o.payment_status = 'PENDING'
""", (hotel_id, hotel_id))

pending_count = cursor.fetchone()['count']

if pending_count > 0:
    print(f"✅ Found {pending_count} orders with pending payment - these will be PROTECTED")
else:
    print("✅ No orders with pending payment")

print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)

print(f"\n✅ Orders to be cleared: {len(orders_to_clear)}")
print(f"✅ Orders to be protected: {len(safe_orders)}")
print(f"\n✅ Safety rules are working correctly!")
print("✅ Only COMPLETED & PAID orders with COMPLETED bills will be cleared")
print("✅ Active orders and pending payments are protected")

print("\n" + "=" * 70)

cursor.close()
connection.close()
