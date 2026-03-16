#!/usr/bin/env python
"""Verify tip-related database schema"""

from database.db import get_db_connection

def verify_schema():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 60)
    print("BILLS TABLE SCHEMA")
    print("=" * 60)
    
    cursor.execute('DESCRIBE bills')
    cols = cursor.fetchall()
    
    has_tip_amount = False
    has_waiter_id = False
    
    for col in cols:
        print(f"  {col['Field']:20s} {col['Type']:20s} {col['Null']:5s} {col['Key']:5s} {col['Default']}")
        if col['Field'] == 'tip_amount':
            has_tip_amount = True
        if col['Field'] == 'waiter_id':
            has_waiter_id = True
    
    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    
    if has_tip_amount:
        print("✓ tip_amount column EXISTS in bills table")
    else:
        print("✗ tip_amount column MISSING in bills table")
    
    if has_waiter_id:
        print("✓ waiter_id column EXISTS in bills table")
    else:
        print("⚠ waiter_id column MISSING in bills table")
        print("  Note: waiter_id is in table_orders, will fetch from there")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    verify_schema()
