#!/usr/bin/env python3
"""
Test script to verify dynamic GST feature implementation
"""

from database.db import get_db_connection

def test_gst_schema():
    """Test if gst_percentage column exists in hotels table"""
    print("=" * 60)
    print("Testing Dynamic GST Feature Implementation")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if gst_percentage column exists in hotels table
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'gst_percentage'")
        result = cursor.fetchone()
        
        if result:
            print("✓ gst_percentage column EXISTS in hotels table")
            print(f"  Column details: {result}")
        else:
            print("✗ gst_percentage column DOES NOT EXIST in hotels table")
            print("  Run the application to auto-create the column")
        
        # Check current GST values for all hotels
        cursor.execute("SELECT id, hotel_name, gst_percentage FROM hotels")
        hotels = cursor.fetchall()
        
        print(f"\n✓ Found {len(hotels)} hotel(s) in database:")
        for hotel in hotels:
            gst = hotel.get('gst_percentage', 'NULL')
            print(f"  - Hotel ID {hotel['id']}: {hotel['hotel_name']} - GST: {gst}%")
        
        # Check if tax_rate column exists in bills table (should already exist)
        cursor.execute("SHOW COLUMNS FROM bills LIKE 'tax_rate'")
        result = cursor.fetchone()
        
        if result:
            print("\n✓ tax_rate column EXISTS in bills table")
            print(f"  Column details: {result}")
        else:
            print("\n✗ tax_rate column DOES NOT EXIST in bills table")
        
        # Check sample bills with their tax rates
        cursor.execute("""
            SELECT id, bill_number, tax_rate, subtotal, tax_amount, total_amount 
            FROM bills 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        bills = cursor.fetchall()
        
        if bills:
            print(f"\n✓ Sample bills (last 5):")
            for bill in bills:
                print(f"  - Bill #{bill['bill_number']}: GST {bill['tax_rate']}% | "
                      f"Subtotal: ₹{bill['subtotal']} | Tax: ₹{bill['tax_amount']} | "
                      f"Total: ₹{bill['total_amount']}")
        else:
            print("\n  No bills found in database")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("Schema Validation Complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gst_schema()
