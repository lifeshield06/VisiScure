"""
Quick test script to verify OTP system is working
Run this to test OTP generation and database connectivity
"""
import sys
from guest_verification.otp_service import OTPService

def test_otp_system():
    """Test OTP system functionality"""
    print("=" * 60)
    print("OTP SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: OTP Generation
    print("\n1. Testing OTP Generation...")
    otp = OTPService.generate_otp()
    if len(otp) == 6 and otp.isdigit():
        print(f"   ✓ Generated OTP: {otp}")
    else:
        print(f"   ✗ Invalid OTP format: {otp}")
        return False
    
    # Test 2: Send OTP (Development Mode)
    print("\n2. Testing Send OTP (Development Mode)...")
    test_phone = "9876543210"
    result = OTPService.send_otp(test_phone)
    
    if result.get('success'):
        print(f"   ✓ OTP sent successfully")
        print(f"   Message: {result.get('message')}")
        if result.get('otp_debug'):
            print(f"   Debug OTP: {result.get('otp_debug')}")
    else:
        print(f"   ✗ Failed to send OTP: {result.get('message')}")
        return False
    
    # Test 3: Verify OTP
    print("\n3. Testing OTP Verification...")
    if result.get('otp_debug'):
        verify_result = OTPService.verify_otp(test_phone, result.get('otp_debug'))
        if verify_result.get('success'):
            print(f"   ✓ OTP verified successfully")
            print(f"   Message: {verify_result.get('message')}")
        else:
            print(f"   ✗ Verification failed: {verify_result.get('message')}")
            return False
    else:
        print("   ⊘ Skipping verification test (no debug OTP)")
    
    # Test 4: Check Verification Status
    print("\n4. Testing Verification Status Check...")
    status_result = OTPService.check_verification_status(test_phone)
    if status_result.get('success'):
        print(f"   ✓ Status check successful")
        print(f"   Verified: {status_result.get('verified')}")
        print(f"   Message: {status_result.get('message')}")
    else:
        print(f"   ✗ Status check failed: {status_result.get('message')}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nOTP System is ready to use!")
    print("\nNext steps:")
    print("1. Start Flask server: python3.14 app.py")
    print("2. Open guest verification form")
    print("3. Enter 10-digit phone number")
    print("4. Check console for OTP code")
    print("5. Enter OTP and verify")
    print("\n" + "=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_otp_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
