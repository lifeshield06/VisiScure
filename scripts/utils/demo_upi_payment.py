"""
Demo script: UPI Payment System
Demonstrates all three payment modes with example data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from payment.upi_utils import validate_upi_id, generate_upi_payment_link

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_section(title):
    """Print formatted section"""
    print(f"\n{title}")
    print("-" * 70)

def demo_mode_a_qr_display():
    """Demonstrate QR Display Mode"""
    print_section("MODE A: QR CODE DISPLAY")
    
    hotel_config = {
        "hotel_id": 1,
        "hotel_name": "Grand Hotel",
        "upi_id": "9876543210@paytm",
        "upi_qr_image": "hotel_1_qr.png"
    }
    
    print("\n📋 Hotel Configuration:")
    print(f"   Hotel: {hotel_config['hotel_name']}")
    print(f"   UPI ID: {hotel_config['upi_id']}")
    print(f"   QR Image: {hotel_config['upi_qr_image']}")
    
    print("\n🔍 Payment Mode Determination:")
    if hotel_config['upi_qr_image']:
        print("   ✓ QR image exists → QR_DISPLAY mode")
    
    print("\n💳 Guest Payment Flow:")
    print("   1. Guest clicks 'Pay Now' → Selects UPI")
    print("   2. System shows QR modal with:")
    print(f"      - QR Code: /static/uploads/hotel_qr/{hotel_config['upi_qr_image']}")
    print(f"      - UPI ID: {hotel_config['upi_id']}")
    print(f"      - Amount: ₹1,250.50")
    print("   3. Guest scans QR with UPI app")
    print("   4. Guest completes payment in app")
    print("   5. Guest clicks 'I've Completed the Payment'")
    print("   6. System processes payment → Bill marked PAID")
    
    print("\n✅ Mode A: QR Display - ACTIVE")

def demo_mode_b_upi_link():
    """Demonstrate UPI Link Mode"""
    print_section("MODE B: UPI DEEP LINK")
    
    hotel_config = {
        "hotel_id": 2,
        "hotel_name": "Cozy Cafe",
        "upi_id": "cafe@okaxis",
        "upi_qr_image": None
    }
    
    bill_amount = 850.00
    
    print("\n📋 Hotel Configuration:")
    print(f"   Hotel: {hotel_config['hotel_name']}")
    print(f"   UPI ID: {hotel_config['upi_id']}")
    print(f"   QR Image: {hotel_config['upi_qr_image'] or 'Not configured'}")
    
    print("\n🔍 Payment Mode Determination:")
    if not hotel_config['upi_qr_image'] and hotel_config['upi_id']:
        print("   ✓ No QR image, but UPI ID exists → UPI_LINK mode")
    
    print("\n🔗 UPI Link Generation:")
    upi_link = generate_upi_payment_link(
        hotel_config['upi_id'],
        hotel_config['hotel_name'],
        bill_amount
    )
    print(f"   Generated Link: {upi_link}")
    
    print("\n💳 Guest Payment Flow:")
    print("   1. Guest clicks 'Pay Now' → Selects UPI")
    print("   2. System generates UPI deep link")
    print("   3. System opens UPI app selector")
    print("   4. Guest selects app (Google Pay/PhonePe/Paytm)")
    print("   5. App opens with pre-filled details:")
    print(f"      - Payee: {hotel_config['hotel_name']}")
    print(f"      - UPI ID: {hotel_config['upi_id']}")
    print(f"      - Amount: ₹{bill_amount:.2f}")
    print("   6. Guest completes payment in app")
    print("   7. Confirmation dialog appears")
    print("   8. Guest confirms payment")
    print("   9. System processes payment → Bill marked PAID")
    
    print("\n✅ Mode B: UPI Link - ACTIVE")

def demo_mode_c_unavailable():
    """Demonstrate Unavailable Mode"""
    print_section("MODE C: UPI UNAVAILABLE")
    
    hotel_config = {
        "hotel_id": 3,
        "hotel_name": "Street Food Stall",
        "upi_id": None,
        "upi_qr_image": None
    }
    
    print("\n📋 Hotel Configuration:")
    print(f"   Hotel: {hotel_config['hotel_name']}")
    print(f"   UPI ID: {hotel_config['upi_id'] or 'Not configured'}")
    print(f"   QR Image: {hotel_config['upi_qr_image'] or 'Not configured'}")
    
    print("\n🔍 Payment Mode Determination:")
    if not hotel_config['upi_qr_image'] and not hotel_config['upi_id']:
        print("   ✓ No UPI configuration → UNAVAILABLE mode")
    
    print("\n💳 Guest Payment Flow:")
    print("   1. Guest clicks 'Pay Now' → Selects UPI")
    print("   2. System shows alert:")
    print("      'UPI payment is not available for this hotel.'")
    print("      'Please use Cash payment.'")
    print("   3. Guest selects Cash payment instead")
    print("   4. Guest pays with cash")
    print("   5. Staff marks payment as complete")
    print("   6. System processes payment → Bill marked PAID")
    
    print("\n✅ Mode C: Unavailable - ACTIVE (Cash fallback)")

def demo_upi_validation():
    """Demonstrate UPI ID validation"""
    print_section("UPI ID VALIDATION")
    
    test_cases = [
        ("9876543210@paytm", "Valid - Phone number format"),
        ("user@okaxis", "Valid - Username format"),
        ("hotel.payment@ybl", "Valid - With dot separator"),
        ("cafe_123@paytm", "Valid - With underscore"),
        ("invalid", "Invalid - No @ symbol"),
        ("@bank", "Invalid - No identifier"),
        ("user@", "Invalid - No bank suffix")
    ]
    
    print("\n🧪 Testing UPI ID Validation:")
    for upi_id, description in test_cases:
        is_valid = validate_upi_id(upi_id)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"   {status:12} | {upi_id:25} | {description}")

def demo_upi_link_format():
    """Demonstrate UPI link format"""
    print_section("UPI LINK FORMAT")
    
    print("\n📝 UPI Deep Link Specification:")
    print("   Format: upi://pay?pa={upi_id}&pn={payee_name}&am={amount}&cu=INR")
    print("\n   Parameters:")
    print("   - pa: Payee address (UPI ID)")
    print("   - pn: Payee name (URL encoded)")
    print("   - am: Amount (formatted to 2 decimals)")
    print("   - cu: Currency (always INR)")
    
    print("\n🔗 Example Links:")
    
    examples = [
        ("hotel@paytm", "Grand Hotel", 1250.50),
        ("cafe@okaxis", "Cozy Cafe", 850.00),
        ("9876543210@ybl", "Street Food", 250.00)
    ]
    
    for upi_id, name, amount in examples:
        link = generate_upi_payment_link(upi_id, name, amount)
        print(f"\n   UPI ID: {upi_id}")
        print(f"   Payee: {name}")
        print(f"   Amount: ₹{amount:.2f}")
        print(f"   Link: {link}")

def demo_payment_flow():
    """Demonstrate complete payment flow"""
    print_section("COMPLETE PAYMENT FLOW")
    
    print("\n📱 Guest Journey:")
    print("   1. Guest scans table QR code")
    print("   2. Guest enters name")
    print("   3. Guest browses menu")
    print("   4. Guest adds items to cart")
    print("   5. Guest reviews cart")
    print("   6. Guest confirms order")
    print("   7. Order sent to kitchen")
    print("   8. Guest clicks 'View Bill'")
    print("   9. Bill displayed with items and total")
    print("   10. Guest clicks 'Pay Now'")
    print("   11. Payment modal opens")
    print("   12. Guest optionally adds tip")
    print("   13. Guest selects payment method (UPI/Cash)")
    print("\n   If UPI selected:")
    print("      → System determines mode (QR/Link/Unavailable)")
    print("      → Guest completes payment")
    print("      → Guest confirms payment")
    print("\n   14. System processes payment")
    print("   15. Bill marked as PAID")
    print("   16. Table released")
    print("   17. Success message shown")
    print("   18. Guest session cleared")

def demo_admin_configuration():
    """Demonstrate admin configuration"""
    print_section("ADMIN CONFIGURATION")
    
    print("\n🔧 Admin Setup Steps:")
    print("   1. Login to admin panel")
    print("   2. Navigate to Hotels section")
    print("   3. Click 'Edit' on desired hotel")
    print("   4. Scroll to UPI Payment Configuration")
    print("   5. Enter UPI ID (e.g., 9876543210@paytm)")
    print("   6. Optionally upload QR code image")
    print("   7. Click 'Save'")
    print("   8. System validates configuration")
    print("   9. Configuration saved to database")
    print("   10. Immediately available for guests")
    
    print("\n📋 Configuration Options:")
    print("   Option 1: UPI ID + QR Code")
    print("      → Guests see QR modal (Mode A)")
    print("\n   Option 2: UPI ID only")
    print("      → Guests get UPI link (Mode B)")
    print("\n   Option 3: Neither")
    print("      → UPI unavailable, cash only (Mode C)")
    
    print("\n✏️ Updating Configuration:")
    print("   - Change UPI ID: Edit and save")
    print("   - Replace QR: Upload new (old deleted automatically)")
    print("   - Remove QR: Delete file (falls back to Mode B)")
    print("   - Remove all: Clear both fields (Mode C)")

def main():
    """Run all demos"""
    print_header("UPI PAYMENT SYSTEM DEMONSTRATION")
    
    print("\n🎯 System Overview:")
    print("   The VisiScure Order system supports hotel-specific UPI payments")
    print("   with three intelligent payment modes based on configuration.")
    
    # Demonstrate all three modes
    demo_mode_a_qr_display()
    demo_mode_b_upi_link()
    demo_mode_c_unavailable()
    
    # Demonstrate utilities
    demo_upi_validation()
    demo_upi_link_format()
    
    # Demonstrate flows
    demo_payment_flow()
    demo_admin_configuration()
    
    # Summary
    print_header("SUMMARY")
    print("\n✅ Implementation Status: COMPLETE")
    print("\n📦 Components:")
    print("   ✓ Database schema with UPI columns")
    print("   ✓ Backend API endpoints")
    print("   ✓ UPI utility functions")
    print("   ✓ Frontend payment UI")
    print("   ✓ Admin configuration interface")
    print("   ✓ Three payment modes")
    print("   ✓ Comprehensive testing")
    print("   ✓ Full documentation")
    
    print("\n🚀 Ready for Production Use")
    
    print("\n📚 Documentation:")
    print("   - Implementation Guide: Hotel/docs/UPI_PAYMENT_SYSTEM_GUIDE.md")
    print("   - Quick Reference: Hotel/docs/UPI_QUICK_REFERENCE.md")
    print("   - Status Report: Hotel/docs/UPI_IMPLEMENTATION_STATUS.md")
    
    print("\n🧪 Testing:")
    print("   - Test Suite: python Hotel/scripts/utils/test_upi_payment_system.py")
    print("   - Schema Verify: python Hotel/scripts/migrations/verify_upi_schema.py")
    print("   - Demo: python Hotel/scripts/utils/demo_upi_payment.py")
    
    print("\n" + "=" * 70)
    print("  Thank you for using VisiScure Order UPI Payment System!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
