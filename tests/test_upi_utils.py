"""
Unit tests for UPI utility functions
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from payment.upi_utils import validate_upi_id, generate_upi_payment_link, allowed_qr_file


def test_validate_upi_id():
    """Test UPI ID validation"""
    print("Testing validate_upi_id...")
    
    # Valid UPI IDs
    assert validate_upi_id("9876543210@paytm") == True
    assert validate_upi_id("user@okaxis") == True
    assert validate_upi_id("email.name@ybl") == True
    assert validate_upi_id("test_user@bank") == True
    assert validate_upi_id("user-name@paytm") == True
    
    # Invalid UPI IDs
    assert validate_upi_id("invalid") == False
    assert validate_upi_id("@bank") == False
    assert validate_upi_id("user@") == False
    assert validate_upi_id("") == False
    assert validate_upi_id("us@b") == False  # Too short identifier
    assert validate_upi_id("user@b") == False  # Too short bank
    
    print("✓ validate_upi_id tests passed")


def test_generate_upi_payment_link():
    """Test UPI payment link generation"""
    print("Testing generate_upi_payment_link...")
    
    # Test basic link generation
    link = generate_upi_payment_link("hotel@paytm", "Grand Hotel", 1250.50)
    assert link.startswith("upi://pay?")
    assert "pa=hotel%40paytm" in link
    assert "pn=Grand" in link
    assert "am=1250.50" in link
    assert "cu=INR" in link
    
    # Test with special characters in hotel name
    link = generate_upi_payment_link("test@bank", "Hotel & Restaurant", 100.00)
    assert "pn=Hotel" in link
    assert "am=100.00" in link
    
    # Test amount formatting
    link = generate_upi_payment_link("test@bank", "Hotel", 99.9)
    assert "am=99.90" in link
    
    # Test error cases
    try:
        generate_upi_payment_link("", "Hotel", 100)
        assert False, "Should raise ValueError for empty UPI ID"
    except ValueError:
        pass
    
    try:
        generate_upi_payment_link("test@bank", "", 100)
        assert False, "Should raise ValueError for empty hotel name"
    except ValueError:
        pass
    
    try:
        generate_upi_payment_link("test@bank", "Hotel", 0)
        assert False, "Should raise ValueError for zero amount"
    except ValueError:
        pass
    
    try:
        generate_upi_payment_link("test@bank", "Hotel", -100)
        assert False, "Should raise ValueError for negative amount"
    except ValueError:
        pass
    
    print("✓ generate_upi_payment_link tests passed")


def test_allowed_qr_file():
    """Test QR file validation"""
    print("Testing allowed_qr_file...")
    
    # Valid file types
    assert allowed_qr_file("qr_code.png") == True
    assert allowed_qr_file("qr_code.jpg") == True
    assert allowed_qr_file("qr_code.jpeg") == True
    assert allowed_qr_file("QR_CODE.PNG") == True  # Case insensitive
    assert allowed_qr_file("hotel_123.jpg") == True
    
    # Invalid file types
    assert allowed_qr_file("document.pdf") == False
    assert allowed_qr_file("image.gif") == False
    assert allowed_qr_file("file.txt") == False
    assert allowed_qr_file("noextension") == False
    assert allowed_qr_file("") == False
    
    print("✓ allowed_qr_file tests passed")


if __name__ == "__main__":
    test_validate_upi_id()
    test_generate_upi_payment_link()
    test_allowed_qr_file()
    print("\n✅ All UPI utility tests passed!")
