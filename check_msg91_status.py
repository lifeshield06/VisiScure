"""
Check MSG91 Account Status and Configuration
This script helps diagnose why OTPs are not being delivered
"""
import requests

# Your credentials
AUTH_KEY = "451618A0Y44msLOxW685a4c6aP1"
TEMPLATE_ID = "1407177312988404171"

print("\n" + "="*70)
print("MSG91 ACCOUNT STATUS CHECK")
print("="*70)

# Test 1: Check if auth key is valid
print("\n[TEST 1] Checking Auth Key validity...")
test_url = f"https://control.msg91.com/api/v5/otp?template_id={TEMPLATE_ID}&mobile=919999999999&authkey={AUTH_KEY}&otp=123456"
try:
    response = requests.get(test_url, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('type') == 'success':
            print("✅ Auth Key is VALID")
            print(f"✅ Template ID is VALID")
            print(f"✅ API is accepting requests")
        else:
            print(f"❌ API Error: {data.get('message')}")
    elif response.status_code == 401:
        print("❌ Auth Key is INVALID - Please check your MSG91 dashboard")
    elif response.status_code == 400:
        print("⚠️  Bad Request - Check template ID or phone format")
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Check balance (if API supports it)
print("\n[TEST 2] Checking account balance...")
balance_url = f"https://control.msg91.com/api/balance.php?authkey={AUTH_KEY}"
try:
    response = requests.get(balance_url, timeout=10)
    print(f"Response: {response.text}")
    if response.status_code == 200:
        print("✅ Balance check successful")
    else:
        print("⚠️  Could not check balance")
except Exception as e:
    print(f"⚠️  Balance check not available: {e}")

print("\n" + "="*70)
print("DIAGNOSIS")
print("="*70)
print("""
If Auth Key and Template ID are valid but SMS not received:

1. ⚠️  TEMPLATE NOT APPROVED
   - Login to https://control.msg91.com/
   - Go to: Templates → Find template 1407177312988404171
   - Status must be: "Approved" or "Active"
   - If "Pending": Wait for approval or contact MSG91

2. ⚠️  INSUFFICIENT CREDITS
   - Go to: Wallet/Credits section
   - Check balance (need ₹0.20+ per SMS)
   - Recharge if needed

3. ⚠️  SENDER ID NOT APPROVED
   - Go to: Sender IDs → Check "VisScu"
   - Status must be: "Approved"
   - If not: Use default sender or request approval

4. ⚠️  DND (Do Not Disturb)
   - Your number may be on DND list
   - Transactional SMS should work, promotional won't
   - Try with non-DND number

5. ⚠️  DELIVERY DELAY
   - SMS can take 1-5 minutes
   - Check MSG91 dashboard → Reports → SMS Logs
   - Look for your request_id and delivery status

RECOMMENDED ACTIONS:
1. Login to MSG91 dashboard: https://control.msg91.com/
2. Check template approval status
3. Check wallet balance
4. Check SMS logs for delivery status
5. Contact MSG91 support if needed: support@msg91.com
""")
print("="*70)
