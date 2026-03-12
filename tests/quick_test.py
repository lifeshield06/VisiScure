"""
Quick Test Script - Tests basic functionality with visual feedback
Run this after starting the Flask server
"""

import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test(name, condition, error_msg=""):
    if condition:
        print(f"  ✓ {name}")
        return True
    else:
        print(f"  ✗ {name} - {error_msg}")
        return False

def main():
    print("\n" + "="*60)
    print("QUICK TEST - Smart Restaurant Management System")
    print("="*60)
    
    passed = 0
    failed = 0
    
    # 1. Test Server
    print("\n[1] Server Status")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        if test("Server is running", r.status_code == 200):
            passed += 1
        else:
            failed += 1
    except:
        test("Server is running", False, "Cannot connect")
        print("\n⚠ Server not running! Start with: python app.py")
        return
    
    # 2. Test Public Pages
    print("\n[2] Public Pages")
    pages = ["/", "/admin/login", "/hotel-manager/login-page"]
    for page in pages:
        r = requests.get(f"{BASE_URL}{page}")
        if test(f"GET {page}", r.status_code == 200):
            passed += 1
        else:
            failed += 1
    
    # 3. Test Admin Login
    print("\n[3] Admin Authentication")
    session = requests.Session()
    
    # Invalid login
    r = session.post(f"{BASE_URL}/admin/login", data={
        "username": "wrong", "password": "wrong"
    }, allow_redirects=False)
    if test("Invalid login rejected", "dashboard" not in r.headers.get("Location", "")):
        passed += 1
    else:
        failed += 1
    
    # Valid login
    r = session.post(f"{BASE_URL}/admin/login", data={
        "username": "admin", "password": "admin123"
    }, allow_redirects=False)
    if test("Valid login accepted", r.status_code == 302):
        passed += 1
    else:
        failed += 1
    
    # Follow redirect to dashboard
    r = session.get(f"{BASE_URL}/admin/dashboard", allow_redirects=True)
    if test("Dashboard accessible", r.status_code == 200 and "admin" in r.text.lower()):
        passed += 1
    else:
        failed += 1
        print(f"       Dashboard status: {r.status_code}, length: {len(r.text)}")
    
    # 4. Test Hotel Creation
    print("\n[4] Restaurant Management")
    r = session.post(f"{BASE_URL}/admin/create-hotel", data={
        "name": "Quick Test Hotel",
        "address": "Test Address",
        "city": "Test City",
        "phone": "9999999999"
    }, allow_redirects=False)
    if test("Create hotel", r.status_code in [200, 302]):
        passed += 1
    else:
        failed += 1
    
    r = session.get(f"{BASE_URL}/admin/all-hotels")
    if test("View all hotels", r.status_code == 200):
        passed += 1
    else:
        failed += 1
    
    # 5. Test Manager Creation
    print("\n[5] Manager Management")
    
    # First, we need to get an available hotel ID
    # The add-manager form requires hotel_id since one-hotel-one-manager policy
    # For testing, we'll create a manager but the test may fail if no hotels are available
    
    r = session.post(f"{BASE_URL}/admin/add-manager", data={
        "name": "Quick Test Manager",
        "email": f"quicktest_{int(__import__('time').time())}@test.com",
        "username": f"quicktest_{int(__import__('time').time())}",
        "password": "testpass123",
        "hotel_id": "1"  # Assuming hotel with ID 1 exists
    }, allow_redirects=False)
    # This might fail if hotel_id=1 already has a manager, which is expected
    if test("Create manager (may fail if hotel taken)", r.status_code in [200, 302]):
        passed += 1
    else:
        failed += 1
    
    r = session.get(f"{BASE_URL}/admin/all-managers")
    if test("View all managers", r.status_code == 200):
        passed += 1
    else:
        failed += 1
    
    # 6. Test API Endpoints
    print("\n[6] API Endpoints (require manager login)")
    
    # Summary
    print("\n" + "="*60)
    total = passed + failed
    print(f"Results: {passed}/{total} tests passed")
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} tests failed")
    print("="*60 + "\n")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
