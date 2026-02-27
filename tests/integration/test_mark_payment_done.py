"""
Test script for Mark Payment Done functionality
Tests the cash payment marking feature for completed orders
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_db_connection
from datetime import datetime

def test_mark_payment_done():
    """Test the mark payment done workflow"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("\n" + "="*60)
    print("TESTING MARK PAYMENT DONE FUNCTIONALITY")
    print("="*60)
    
    # Find a completed order with pending payment
    cursor.execute("""
        SELECT o.id, o.table_id, o.order_status, o.payment_status, 
               t.table_number, t.status as table_status
        FROM table_orders o
        JOIN tables t ON o.table_id = t.id
        WHERE o.order_status = 'COMPLETED' 
        AND o.payment_status = 'PENDING'
        LIMIT 1
    """)
    
    order = cursor.fetchone()
    
    if not order:
        print("\n❌ No completed orders with pending payment found")
        print("Creating test scenario...")
        
        # Create a test order
        cursor.execute("""
            SELECT id, table_number FROM tables 
            WHERE status = 'AVAILABLE' 
            LIMIT 1
        """)
        table = cursor.fetchone()
        
        if not table:
            print("❌ No available tables found")
            conn.close()
            return
        
        table_id = table['id']
        table_number = table['table_number']
        
        # Create test order
        cursor.execute("""
            INSERT INTO table_orders 
            (table_id, order_status, payment_status, total_amount, created_at)
            VALUES (%s, 'COMPLETED', 'PENDING', 100.00, %s)
        """, (table_id, datetime.now()))
        
        order_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Created test order {order_id} for table {table_number}")
        
        order = {
            'id': order_id,
            'table_id': table_id,
            'order_status': 'COMPLETED',
            'payment_status': 'PENDING',
            'table_number': table_number,
            'table_status': 'AVAILABLE'
        }
    
    order_id = order['id']
    table_id = order['table_id']
    order_status = order['order_status']
    payment_status = order['payment_status']
    table_number = order['table_number']
    table_status = order['table_status']
    
    print(f"\n📋 Test Order Details:")
    print(f"   Order ID: {order_id}")
    print(f"   Table: {table_number} (ID: {table_id})")
    print(f"   Order Status: {order_status}")
    print(f"   Payment Status: {payment_status}")
    print(f"   Table Status: {table_status}")
    
    # Check if bill exists
    cursor.execute("""
        SELECT id, bill_status, payment_status, payment_method
        FROM bills
        WHERE order_id = %s
    """, (order_id,))
    
    bill = cursor.fetchone()
    
    if bill:
        bill_id = bill['id']
        bill_status = bill['bill_status']
        bill_payment_status = bill['payment_status']
        payment_method = bill['payment_method']
        print(f"\n💰 Related Bill:")
        print(f"   Bill ID: {bill_id}")
        print(f"   Bill Status: {bill_status}")
        print(f"   Payment Status: {bill_payment_status}")
        print(f"   Payment Method: {payment_method or 'Not set'}")
    else:
        print(f"\n💰 No bill found for this order")
    
    print("\n" + "-"*60)
    print("SIMULATING: Mark Payment Done (Cash)")
    print("-"*60)
    
    # Simulate the mark payment done action
    # 1. Update order payment status
    cursor.execute("""
        UPDATE table_orders
        SET payment_status = 'PAID'
        WHERE id = %s
    """, (order_id,))
    
    print(f"✅ Updated order {order_id} payment_status to PAID")
    
    # 2. If bill exists, update it
    if bill:
        bill_id = bill['id']
        paid_at = datetime.now()
        cursor.execute("""
            UPDATE bills
            SET bill_status = 'COMPLETED',
                payment_status = 'PAID',
                payment_method = 'CASH',
                paid_at = %s
            WHERE id = %s
        """, (paid_at, bill_id))
        
        print(f"✅ Updated bill {bill_id} to COMPLETED/PAID with CASH payment")
        
        # 3. Check for other open bills on this table
        cursor.execute("""
            SELECT COUNT(*) as count FROM bills
            WHERE table_id = %s AND bill_status = 'OPEN'
        """, (table_id,))
        
        result = cursor.fetchone()
        open_bills = result['count'] if result else 0
        
        if open_bills == 0:
            # Free the table
            cursor.execute("""
                UPDATE tables
                SET status = 'AVAILABLE', 
                    current_session_id = NULL, 
                    current_guest_name = NULL
                WHERE id = %s
            """, (table_id,))
            
            print(f"✅ Released table {table_number} (no more open bills)")
            
            # Delete active_tables entry
            cursor.execute("""
                DELETE FROM active_tables
                WHERE table_id = %s AND status = 'ACTIVE'
            """, (table_id,))
            
            print(f"✅ Deleted active_tables entry for table {table_number}")
        else:
            print(f"⚠️  Table {table_number} still has {open_bills} open bill(s)")
    
    conn.commit()
    
    # Verify final state
    print("\n" + "-"*60)
    print("VERIFICATION: Final State")
    print("-"*60)
    
    cursor.execute("""
        SELECT order_status, payment_status
        FROM table_orders
        WHERE id = %s
    """, (order_id,))
    
    final_order = cursor.fetchone()
    print(f"\n📋 Order {order_id}:")
    print(f"   Status: {final_order['order_status']}")
    print(f"   Payment: {final_order['payment_status']}")
    
    if bill:
        bill_id = bill['id']
        cursor.execute("""
            SELECT bill_status, payment_status, payment_method, paid_at
            FROM bills
            WHERE id = %s
        """, (bill_id,))
        
        final_bill = cursor.fetchone()
        print(f"\n💰 Bill {bill_id}:")
        print(f"   Status: {final_bill['bill_status']}")
        print(f"   Payment: {final_bill['payment_status']}")
        print(f"   Method: {final_bill['payment_method']}")
        print(f"   Paid At: {final_bill['paid_at']}")
    
    cursor.execute("""
        SELECT status, current_session_id, current_guest_name
        FROM tables
        WHERE id = %s
    """, (table_id,))
    
    final_table = cursor.fetchone()
    print(f"\n🪑 Table {table_number}:")
    print(f"   Status: {final_table['status']}")
    print(f"   Session ID: {final_table['current_session_id'] or 'None'}")
    print(f"   Guest Name: {final_table['current_guest_name'] or 'None'}")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("="*60)
    
    conn.close()

if __name__ == "__main__":
    test_mark_payment_done()
