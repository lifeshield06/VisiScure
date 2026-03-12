"""
Test MSG91 with Correct Template Variables
Template ID: 69b244d394b176db2203e483
Template: Welcome to ##var1##. Your verification OTP is ##OTP##. 
          Please enter this code to complete guest verification. VisiScure Order
"""
import requests
from urllib.parse import quote

# Credentials
AUTH_KEY = "451618A0Y44msLOxW685a4c6aP1"
TEMPLATE_ID = "69b244d394b176db2203e483"

# Test data
phone_number = "917722021558"
otp_code = "789012"
hotel_name = "Tip Top Restaurant"  # This will be used for ##var1##

print("\n" + "="*70)
print("TESTING MSG91 WITH CORRECT TEMPLATE VARIABLES")
print("="*70)
print(f"Template ID: {TEMPLATE_ID}")
print(f"Phone: {phone_number}")
print(f"Hotel Name (var1): {hotel_name}")
print(f"OTP: {otp_code}")
print("\nTemplate Format:")
print("Welcome to ##var1##. Your verification OTP is ##OTP##.")
print("Please enter this code to complete guest verification. VisiScure Order")
print("="*70)

# URL encode hotel name to handle spaces
hotel_name_encoded = quote(hotel_name)
print(f"\nHotel Name (URL encoded): {hotel_name_encoded}")

# Build URL with correct variable names: var1 and otp
url = f"https://control.msg91.com/api/v5/otp?template_id={TEMPLATE_ID}&mobile={phone_number}&authkey={AUTH_KEY}&var1={hotel_name_encoded}&otp={otp_code}"

print(f"\n[TEST] Sending OTP...")
print(f"URL: {url}")

try:
    response = requests.get(url, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('type') == 'success':
            print(f"\n✅ SUCCESS!")
            print(f"Request ID: {data.get('request_id')}")
            print(f"\n📱 CHECK YOUR PHONE: {phone_number}")
            print(f"\nExpected SMS:")
            print(f"Welcome to {hotel_name}. Your verification OTP is {otp_code}.")
            print(f"Please enter this code to complete guest verification. VisiScure Order")
            print(f"\n✅ Template variables are CORRECT!")
        else:
            print(f"\n❌ API Error: {data.get('message')}")
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*70)
print("CONFIGURATION SUMMARY")
print("="*70)
print(f"✓ Template ID: {TEMPLATE_ID}")
print(f"✓ Template Variables: var1, otp")
print(f"✓ var1 = {hotel_name} (encoded: {hotel_name_encoded})")
print(f"✓ otp = {otp_code}")
print("="*70)
