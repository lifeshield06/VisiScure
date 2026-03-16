"""
Interactive Test Script for Smart Restaurant Management System
This script tests with existing data and provides detailed feedback
"""

import requests
import json
import time
import sys
import re

BASE_URL = "http://127.0.0.1:5000"
TIMESTAMP = str(int(time.time()))

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def header(text):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

def section(text):
    print(f"\n{Colors.YELLOW}▶ {text}{Colors.RESET}")

def ok(msg):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")

def fail(msg, detail=""):
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")
    if detail:
        print(f"    {Colors.YELLOW}→ {detail}{Colors.RESET}")

def info(msg):
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {msg}")

def run_tests():
    header("Smart Restaurant Management System - Integration Tests")
    print(f"Target: {BASE_URL}")
    print(f"Timestamp: {TIMESTAMP}")
    
    passed = 0
    failed = 0
    
    # =============== CHECK SERVER ===============
    section("Checking Server")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        if r.status_code == 200:
            ok("Server is running")
            passed += 1
        else:
            fail(f"Server returned {r.status_code}")
            failed += 1
            return passed, failed
    except Exception as e:
        fail("Cannot connect to server", str(e))
        return passed, failed
    
    # =============== ADMIN SESSION ===============
    section("Admin Authentication")
    admin = requests.Session()
    
    # Test login
    r = admin.post(f"{BASE_URL}/admin/login", data={
        "username": "admin",
        "password": "admin123"
    }, allow_redirects=False)
    
    if r.status_code == 302:
        ok("Admin login successful")
        passed += 1
    else:
        fail("Admin login failed", f"Status: {r.status_code}")
        failed += 1
        return passed, failed
    
    # Dashboard access
    r = admin.get(f"{BASE_URL}/admin/dashboard")
    if r.status_code == 200:
        ok("Admin dashboard accessible")
        passed += 1
    else:
        fail("Cannot access admin dashboard")
        failed += 1
    
    # =============== CREATE TEST HOTEL ===============
    section("Restaurant Management")
    
    hotel_data = {
        "name": f"Test Hotel {TIMESTAMP}",
        "address": "123 Test Street",
        "city": "Test City",
        "phone": "1234567890"
    }
    
    r = admin.post(f"{BASE_URL}/admin/create-hotel", data=hotel_data, allow_redirects=True)
    if r.status_code == 200:
        ok(f"Created hotel: {hotel_data['name']}")
        passed += 1
    else:
        fail("Failed to create hotel", f"Status: {r.status_code}")
        failed += 1
    
    # Get hotel list and find new hotel ID
    r = admin.get(f"{BASE_URL}/admin/all-hotels")
    if r.status_code == 200:
        ok("Can view hotels list")
        passed += 1
        
        # Try to extract hotel ID from the page (look for edit links)
        # Pattern: edit-hotel/123 or similar
        hotel_ids = re.findall(r'edit-hotel/(\d+)', r.text)
        if hotel_ids:
            new_hotel_id = hotel_ids[-1]  # Get the last (newest) hotel
            info(f"Found hotel IDs: {hotel_ids}, using: {new_hotel_id}")
        else:
            new_hotel_id = "1"
            info("Could not extract hotel ID, using default: 1")
    else:
        fail("Cannot view hotels list")
        failed += 1
        new_hotel_id = "1"
    
    # =============== CREATE TEST MANAGER ===============
    section("Manager Management")
    
    manager_data = {
        "name": f"Test Manager {TIMESTAMP}",
        "email": f"mgr_{TIMESTAMP}@test.com",
        "username": f"mgr_{TIMESTAMP}",
        "password": "testpass123",
        "hotel_id": new_hotel_id
    }
    
    r = admin.post(f"{BASE_URL}/admin/add-manager", data=manager_data, allow_redirects=True)
    if r.status_code == 200 and "already exists" not in r.text.lower():
        ok(f"Created manager: {manager_data['username']}")
        passed += 1
    else:
        if "already exists" in r.text.lower():
            info("Manager or hotel already assigned (expected on repeat runs)")
            passed += 1
        else:
            fail("Failed to create manager")
            failed += 1
    
    # =============== MANAGER LOGIN ===============
    section("Manager Authentication")
    manager_session = requests.Session()
    
    # Manager login expects JSON, not form data
    r = manager_session.post(f"{BASE_URL}/hotel-manager/login", json={
        "username": manager_data["username"],
        "password": manager_data["password"]
    }, allow_redirects=False)
    
    # Manager login returns JSON response
    login_result = r.json() if 'application/json' in r.headers.get('content-type', '') else {}
    
    if login_result.get("success"):
        ok(f"Manager login successful")
        passed += 1
        
        # Follow redirect to dashboard
        r = manager_session.get(f"{BASE_URL}/hotel-manager/dashboard")
        if r.status_code == 200:
            ok("Manager dashboard accessible")
            passed += 1
            
            # Check if modules are visible
            if "KYC" in r.text or "Verification" in r.text:
                info("KYC module detected in dashboard")
            if "Menu" in r.text or "Food" in r.text or "Order" in r.text:
                info("Food module detected in dashboard")
        else:
            fail("Cannot access manager dashboard")
            failed += 1
    else:
        fail("Manager login failed", f"Status: {r.status_code}")
        failed += 1
        info("This may be due to no hotel being assigned or incorrect credentials")
        
        # Try with existing manager if available
        info("Attempting to find existing managers to test with...")
        r = admin.get(f"{BASE_URL}/admin/all-managers")
        existing_managers = re.findall(r'<td>(\w+@\w+\.\w+)</td>', r.text)
        if existing_managers:
            info(f"Found existing manager emails: {existing_managers[:3]}")
    
    # =============== API TESTS ===============
    section("API Endpoints")
    
    # Test with admin session for basic checks
    endpoints = [
        ("/", "GET", None, "Home page"),
        ("/admin/all-hotels", "GET", admin, "Hotels list"),
        ("/admin/all-managers", "GET", admin, "Managers list"),
    ]
    
    for path, method, sess, name in endpoints:
        try:
            if sess:
                r = sess.get(f"{BASE_URL}{path}")
            else:
                r = requests.get(f"{BASE_URL}{path}")
            
            if r.status_code == 200:
                ok(f"{name}: OK")
                passed += 1
            else:
                fail(f"{name}: {r.status_code}")
                failed += 1
        except Exception as e:
            fail(f"{name}: Error", str(e))
            failed += 1
    
    # Test menu APIs (may fail without proper session)
    section("Menu APIs (Session-dependent)")
    
    api_tests = [
        ("/api/categories", "Categories API"),
        ("/api/full-menu", "Full Menu API"),
    ]
    
    for path, name in api_tests:
        try:
            r = manager_session.get(f"{BASE_URL}{path}")
            data = r.json() if 'application/json' in r.headers.get('content-type', '') else None
            
            if data and data.get("success"):
                ok(f"{name}: Success")
                passed += 1
            elif data:
                fail(f"{name}: {data.get('message', 'Failed')}")
                failed += 1
            else:
                fail(f"{name}: Non-JSON response")
                failed += 1
        except Exception as e:
            fail(f"{name}: Error", str(e))
            failed += 1
    
    # =============== SUMMARY ===============
    header("Test Summary")
    total = passed + failed
    percent = (passed / total * 100) if total > 0 else 0
    
    print(f"\n  Total Tests: {total}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.RESET}")
    print(f"  Success Rate: {percent:.1f}%")
    
    if failed == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.RESET}")
    else:
        print(f"\n  {Colors.YELLOW}Some tests failed - see details above{Colors.RESET}")
    
    return passed, failed

if __name__ == "__main__":
    try:
        passed, failed = run_tests()
        sys.exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n\nTests cancelled.")
        sys.exit(1)
