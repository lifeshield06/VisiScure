"""
Test Final MSG91 Template ID: 69b244d394b176db2203e483
"""
import requests

# Final credentials
AUTH_KEY = "451618A0Y44msLOxW685a4c6aP1"
TEMPLATE_ID = "69b244d394b176db2203e483"

# Test data
phone_number = "917722021558"
otp_code = "123456"
hotel_name = "VisiScure Order"

print("\n" + "="*70)
print("TESTING FINAL MSG91 TEMPLATE ID")
print("="*70)
print(f"Template ID: {TEMPLATE_ID}")
print(f"Phone: {phone_number}")
print(f"Hotel Name: {hotel_name}")
print(f"OTP: {otp_code}")
print("="*70)

# Build URL with template variables
url = f"https://control.msg91.com/api/v5/otp?template_id={TEMPLATE_ID}&mobile={phone_number}&authkey={AUTH_KEY}&alphanumeric={hotel_name}&numeric={otp_code}"

print(f"\n[TEST] Sending OTP with template {TEMPLATE_ID}...")

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
            print(f"🔐 OTP: {otp_code}")
            print(f"\nExpected SMS:")
            print(f"Welcome to {hotel_name}. Your verification OTP is {otp_code}.")
            print(f"Please enter this code to complete guest verification. VisiScure Order")
        else:
            print(f"\n❌ API Error: {data.get('message')}")
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*70)
print("If SMS not received:")
print("1. Check MSG91 Dashboard → Reports → SMS Logs")
print("2. Verify template 69b244d394b176db2203e483 is approved")
print("3. Check wallet balance")
print("4. Check sender ID 'VisScu' is approved")
print("="*70)
