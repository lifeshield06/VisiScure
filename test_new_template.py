"""
Test New MSG91 Template ID
"""
import requests

# New credentials
AUTH_KEY = "451618A0Y44msLOxW685a4c6aP1"
NEW_TEMPLATE_ID = "68ec8429cec777483f422df6"

# Test phone number
phone_number = "917722021558"
otp_code = "123456"
hotel_name = "VisiScure Order"

print("\n" + "="*70)
print("TESTING NEW MSG91 TEMPLATE ID")
print("="*70)
print(f"Template ID: {NEW_TEMPLATE_ID}")
print(f"Phone: {phone_number}")
print(f"OTP: {otp_code}")
print("="*70)

# Test with new template ID
url = f"https://control.msg91.com/api/v5/otp?template_id={NEW_TEMPLATE_ID}&mobile={phone_number}&authkey={AUTH_KEY}&otp={otp_code}&OTP={otp_code}&hotel_name={hotel_name}"

print("\n[TEST] Sending OTP with new template...")
try:
    response = requests.get(url, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('type') == 'success':
            print(f"\n✅ SUCCESS!")
            print(f"Request ID: {data.get('request_id')}")
            print(f"\n📱 Check your phone {phone_number} for OTP!")
            print(f"🔐 OTP: {otp_code}")
        else:
            print(f"\n❌ API Error: {data.get('message')}")
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*70)
