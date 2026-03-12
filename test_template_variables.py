"""
Test MSG91 Template with Correct Variables
Template: Welcome to {#alphanumeric#}. Your verification OTP is {#numeric#}. Please enter this code to complete guest verification. VisiScure Order
"""
import requests

# Credentials
AUTH_KEY = "451618A0Y44msLOxW685a4c6aP1"
TEMPLATE_ID = "69b244d394b176db2203e483"

# Test data
phone_number = "917722021558"
otp_code = "123456"
hotel_name = "VisiScure Order"

print("\n" + "="*70)
print("TESTING MSG91 TEMPLATE WITH CORRECT VARIABLES")
print("="*70)
print(f"Template ID: {TEMPLATE_ID}")
print(f"Phone: {phone_number}")
print(f"Hotel Name (alphanumeric): {hotel_name}")
print(f"OTP (numeric): {otp_code}")
print("\nTemplate Format:")
print("Welcome to {#alphanumeric#}. Your verification OTP is {#numeric#}.")
print("Please enter this code to complete guest verification. VisiScure Order")
print("="*70)

# Build URL with correct variable names
url = f"https://control.msg91.com/api/v5/otp?template_id={TEMPLATE_ID}&mobile={phone_number}&authkey={AUTH_KEY}&alphanumeric={hotel_name}&numeric={otp_code}"

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
        else:
            print(f"\n❌ API Error: {data.get('message')}")
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*70)
