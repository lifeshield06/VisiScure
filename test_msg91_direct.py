"""
Direct MSG91 API Test Script
Tests MSG91 OTP API with your credentials
"""
import requests
import json

# Your MSG91 credentials
MSG91_AUTH_KEY = "451618A0Y44msLOxW685a4c6aP1"
MSG91_TEMPLATE_ID = "1407177312988404171"
MSG91_SENDER_ID = "VisScu"

# Test phone number (replace with your number)
phone_number = input("Enter 10-digit mobile number: ").strip()
if not phone_number.startswith('91'):
    phone_number = '91' + phone_number

# Generate test OTP
otp_code = "123456"
hotel_name = "VisiScure Order"

print("\n" + "="*70)
print("MSG91 DIRECT API TEST")
print("="*70)
print(f"Phone: {phone_number}")
print(f"OTP: {otp_code}")
print(f"Hotel: {hotel_name}")
print(f"Template ID: {MSG91_TEMPLATE_ID}")
print(f"Auth Key: {MSG91_AUTH_KEY[:10]}...")
print("="*70)

# Method 1: GET request with query parameters
print("\n[TEST 1] Trying GET request with query parameters...")
url1 = f"https://control.msg91.com/api/v5/otp?template_id={MSG91_TEMPLATE_ID}&mobile={phone_number}&authkey={MSG91_AUTH_KEY}&otp={otp_code}"

try:
    response1 = requests.get(url1, timeout=10)
    print(f"Status Code: {response1.status_code}")
    print(f"Response: {response1.text}")
    if response1.status_code == 200:
        print("✅ Method 1 SUCCESS!")
    else:
        print("❌ Method 1 FAILED")
except Exception as e:
    print(f"❌ Method 1 ERROR: {e}")

# Method 2: POST request with JSON body
print("\n[TEST 2] Trying POST request with JSON body...")
url2 = f"https://control.msg91.com/api/v5/otp?template_id={MSG91_TEMPLATE_ID}&mobile={phone_number}&authkey={MSG91_AUTH_KEY}&otp={otp_code}"
payload2 = {
    "OTP": otp_code,
    "hotel_name": hotel_name
}
headers2 = {"Content-Type": "application/json"}

try:
    response2 = requests.post(url2, json=payload2, headers=headers2, timeout=10)
    print(f"Status Code: {response2.status_code}")
    print(f"Response: {response2.text}")
    if response2.status_code == 200:
        print("✅ Method 2 SUCCESS!")
    else:
        print("❌ Method 2 FAILED")
except Exception as e:
    print(f"❌ Method 2 ERROR: {e}")

# Method 3: POST with form data
print("\n[TEST 3] Trying POST request with form data...")
url3 = "https://control.msg91.com/api/v5/otp"
data3 = {
    "template_id": MSG91_TEMPLATE_ID,
    "mobile": phone_number,
    "authkey": MSG91_AUTH_KEY,
    "otp": otp_code,
    "OTP": otp_code,
    "hotel_name": hotel_name
}

try:
    response3 = requests.post(url3, data=data3, timeout=10)
    print(f"Status Code: {response3.status_code}")
    print(f"Response: {response3.text}")
    if response3.status_code == 200:
        print("✅ Method 3 SUCCESS!")
    else:
        print("❌ Method 3 FAILED")
except Exception as e:
    print(f"❌ Method 3 ERROR: {e}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
