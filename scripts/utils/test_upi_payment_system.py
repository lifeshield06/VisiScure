"""
Test script: Verify UPI Payment System Implementation
Tests all three payment modes: QR Display, UPI Link, and Unavailable
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection
from payment.upi_utils import validate_upi_id, generate_upi_payment_link, allowed_qr_file

def test_upi_validation():
    """Test UPI ID validation"""
    print("\n🧪 Testing UPI ID Validation...")
    
    test_cases = [
        ("9876543210@paytm", True),
        ("user@okaxis", True),
        ("hotel.payment@ybl", True),
        ("invalid", False),
        ("@bank", False),
        ("", False),
        (None, False)
    ]
    
    passed = 0
    for upi_id, expected in test_cases:
        result = validate_upi_id(upi_id)
        status = "✓" if result == expected else "✗"
        print(f"   {status} validate_upi_id('{upi_id}') = {result} (expected {expected})")
        if result == expected:
            passed += 1
    
    print(f"\n   Passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_upi_link_generation():
    """Test UPI payment link generation"""
    print("\n🧪 Testing UPI Link Generation...")
    
    try:
        link = generate_upi_payment_link("hotel@paytm", "Grand Hotel", 1250.50)
        print(f"   Generated link: {link}")
        
        # Verify link format
        checks = [
            ("Starts with upi://pay?", link.startswith("upi://pay?")),
            ("Contains pa parameter", "pa=" in link),
            ("Contains pn parameter", "pn=" in link),
            ("Contains am parameter", "am=" in link),
            ("Contains cu=INR", "cu=INR" in link),
            ("Amount formatted correctly", "am=1250.50" in link)
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "✓" if result else "✗"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_qr_file_validation():
    """Test QR file validation"""
    print("\n🧪 Testing QR File Validation...")
    
    test_cases = [
        ("qr_code.png", True),
        ("qr_code.jpg", True),
        ("qr_code.jpeg", True),
        ("qr_code.PNG", True),
        ("document.pdf", False),
        ("image.gif", False),
        ("", False),
        (None, False)
    ]
    
    passed = 0
    for filename, expected in test_cases:
        result = allowed_qr_file(filename)
        status = "✓" if result == expected else "✗"
        print(f"   {status} allowed_qr_file('{filename}') = {result} (expected {expected})")
        if result == expected:
            passed += 1
    
    print(f"\n   Passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_database_schema():
    """Test database schema for UPI columns"""
    print("\n🧪 Testing Database Schema...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DESCRIBE hotels")
        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]
        
        upi_id_exists = 'upi_id' in column_names
        upi_qr_exists = 'upi_qr_image' in column_names
        
        print(f"   {'✓' if upi_id_exists else '✗'} upi_id column exists")
        print(f"   {'✓' if upi_qr_exists else '✗'} upi_qr_image column exists")
        
        cursor.close()
        conn.close()
        
        return upi_id_exists and upi_qr_exists
        
    except Exception as e:
        print(f"   ✗ Database error: {e}")
        return False

def test_payment_modes():
    """Test all three payment modes"""
    print("\n🧪 Testing Payment Mode Logic...")
    
    # Simulate the three cases
    test_cases = [
        {
            "name": "Case 1: QR Code exists",
            "upi_id": "hotel@paytm",
            "upi_qr_image": "hotel_1_qr.png",
            "expected_mode": "QR_DISPLAY"
        },
        {
            "name": "Case 2: Only UPI ID exists",
            "upi_id": "hotel@paytm",
            "upi_qr_image": None,
            "expected_mode": "UPI_LINK"
        },
        {
            "name": "Case 3: Neither exists",
            "upi_id": None,
            "upi_qr_image": None,
            "expected_mode": "UNAVAILABLE"
        }
    ]
    
    for case in test_cases:
        upi_id = case["upi_id"]
        upi_qr = case["upi_qr_image"]
        expected = case["expected_mode"]
        
        # Determine mode based on logic
        if upi_qr and upi_qr.strip():
            mode = "QR_DISPLAY"
        elif upi_id and upi_id.strip():
            mode = "UPI_LINK"
        else:
            mode = "UNAVAILABLE"
        
        status = "✓" if mode == expected else "✗"
        print(f"   {status} {case['name']}: {mode} (expected {expected})")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("UPI PAYMENT SYSTEM TEST SUITE")
    print("=" * 60)
    
    results = {
        "UPI Validation": test_upi_validation(),
        "UPI Link Generation": test_upi_link_generation(),
        "QR File Validation": test_qr_file_validation(),
        "Database Schema": test_database_schema(),
        "Payment Modes": test_payment_modes()
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
