"""
Test script for MSG91 OTP integration
Run this to verify MSG91 API is working correctly
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from guest_verification.otp_service import OTPService

def test_msg91_integration():
    """Test MSG91 OTP sending"""
    print("\n" + "="*70)
    print("MSG91 OTP INTEGRATION TEST")
    print("="*70)
    
    # Get test phone number
    phone = input("\nEnter 10-digit mobile number to test: ").strip()
    
    if not phone or len(phone) != 10 or not phone.isdigit():
        print("❌ Invalid phone number. Must be 10 digits.")
        return
    
    hotel_name = "VisiScure Order Test"
    
    print(f"\n📱 Sending OTP to: {phone}")
    print(f"🏨 Hotel name: {hotel_name}")
    print("\nPlease wait...")
    
    # Send OTP
    result = OTPService.send_otp(phone, hotel_name)
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"Success: {result.get('success')}")
    print(f"Message: {result.get('message')}")
    
    if 'otp_debug' in result:
        print(f"\n🔐 DEBUG OTP: {result.get('otp_debug')}")
        print("(This OTP is shown for testing purposes)")
    
    print("="*70 + "\n")
    
    if result.get('success'):
        # Test verification
        verify = input("\nDo you want to test OTP verification? (y/n): ").strip().lower()
        
        if verify == 'y':
            otp_code = input("Enter the OTP you received: ").strip()
            
            if otp_code:
                print("\nVerifying OTP...")
                verify_result = OTPService.verify_otp(phone, otp_code)
                
                print("\n" + "="*70)
                print("VERIFICATION RESULT")
                print("="*70)
                print(f"Success: {verify_result.get('success')}")
                print(f"Message: {verify_result.get('message')}")
                print("="*70 + "\n")

if __name__ == "__main__":
    try:
        test_msg91_integration()
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
