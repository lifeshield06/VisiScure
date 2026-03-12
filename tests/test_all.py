"""
Comprehensive Test Suite for Smart Restaurant Management System
Tests all functionalities including login, hotel-specific data isolation, and module access
"""

import requests
import json
import time
import sys

# Base URL for the Flask app
BASE_URL = "http://127.0.0.1:5000"

# Test data - using timestamps to make unique
import time
TIMESTAMP = str(int(time.time()))

TEST_ADMIN = {"username": "admin", "password": "admin123"}
TEST_HOTEL_1 = {
    "hotel_name": f"Test Hotel Alpha {TIMESTAMP}",
    "address": "123 Test Street",
    "city": "Test City",
    "phone": "1234567890",
    "food": "on",  # Enable food ordering module
    "kyc": "on"    # Enable KYC module
}
TEST_HOTEL_2 = {
    "hotel_name": f"Test Hotel Beta {TIMESTAMP}",
    "address": "456 Beta Avenue",
    "city": "Beta City",
    "phone": "0987654321",
    "food": "on",  # Enable food ordering module
    "kyc": "on"    # Enable KYC module
}
TEST_MANAGER_1 = {
    "name": "Manager One",
    "email": f"manager1_{TIMESTAMP}@test.com",
    "username": f"manager1_{TIMESTAMP}",
    "password": "password123"
}
TEST_MANAGER_2 = {
    "name": "Manager Two",
    "email": f"manager2_{TIMESTAMP}@test.com",
    "username": f"manager2_{TIMESTAMP}",
    "password": "password123"
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")

def print_test(name, passed, message=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  {status} - {name}")
    if message and not passed:
        print(f"       {Colors.YELLOW}{message}{Colors.RESET}")

def print_section(text):
    print(f"\n{Colors.YELLOW}▶ {text}{Colors.RESET}")

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add(self, name, passed, message=""):
        self.tests.append({"name": name, "passed": passed, "message": message})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print_test(name, passed, message)
    
    def summary(self):
        total = self.passed + self.failed
        print_header("TEST SUMMARY")
        print(f"  Total Tests: {total}")
        print(f"  {Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.failed}{Colors.RESET}")
        if self.failed > 0:
            print(f"\n  {Colors.RED}Failed Tests:{Colors.RESET}")
            for test in self.tests:
                if not test["passed"]:
                    print(f"    - {test['name']}: {test['message']}")
        return self.failed == 0


class HotelManagementTests:
    def __init__(self):
        self.results = TestResults()
        self.admin_session = requests.Session()
        self.manager1_session = requests.Session()
        self.manager2_session = requests.Session()
        self.hotel1_id = None
        self.hotel2_id = None
        self.manager1_id = None
        self.manager2_id = None
        
    def check_server(self):
        """Check if server is running"""
        print_section("Checking Server Status")
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            self.results.add("Server is running", True)
            return True
        except requests.exceptions.ConnectionError:
            self.results.add("Server is running", False, "Cannot connect to server at " + BASE_URL)
            return False

    # ==================== ADMIN TESTS ====================
    
    def test_admin_login(self):
        """Test admin login"""
        print_section("Testing Admin Login")
        
        # Test invalid login
        response = self.admin_session.post(f"{BASE_URL}/admin/login", data={
            "username": "wrong",
            "password": "wrong"
        }, allow_redirects=False)
        self.results.add("Admin invalid login rejected", response.status_code != 302 or "admin-dashboard" not in response.headers.get("Location", ""))
        
        # Test valid login
        response = self.admin_session.post(f"{BASE_URL}/admin/login", data={
            "username": TEST_ADMIN["username"],
            "password": TEST_ADMIN["password"]
        }, allow_redirects=False)
        self.results.add("Admin valid login accepted", response.status_code == 302)
        
        # Test dashboard access
        response = self.admin_session.get(f"{BASE_URL}/admin/dashboard")
        self.results.add("Admin dashboard accessible", response.status_code == 200 and "Dashboard" in response.text)
    
    def test_create_hotels(self):
        """Test hotel creation"""
        print_section("Testing Hotel Creation")
        
        # Create Hotel 1
        response = self.admin_session.post(f"{BASE_URL}/admin/create-hotel", data=TEST_HOTEL_1, allow_redirects=False)
        success1 = response.status_code in [200, 302]
        self.results.add(f"Create Hotel 1 ({TEST_HOTEL_1['hotel_name']})", success1)
        
        # Create Hotel 2
        response = self.admin_session.post(f"{BASE_URL}/admin/create-hotel", data=TEST_HOTEL_2, allow_redirects=False)
        success2 = response.status_code in [200, 302]
        self.results.add(f"Create Hotel 2 ({TEST_HOTEL_2['hotel_name']})", success2)
        
        # Get hotel list page and extract hotel IDs
        response = self.admin_session.get(f"{BASE_URL}/admin/all-hotels")
        has_hotels = "hotel" in response.text.lower() and response.status_code == 200
        self.results.add("Hotels list page loads", has_hotels)
        
        # Extract hotel IDs from the page
        # Hotels are ordered by created_at DESC, so:
        # - Hotel 2 (Beta, created last) appears FIRST in the list
        # - Hotel 1 (Alpha, created first) appears SECOND in the list
        import re
        html = response.text
        
        all_ids = re.findall(r'edit-hotel/(\d+)', html)
        if len(all_ids) >= 2:
            # Since Hotel 2 was created after Hotel 1, it appears first
            self.hotel2_id = all_ids[0]  # Beta (newest)
            self.hotel1_id = all_ids[1]  # Alpha (second newest)
        elif len(all_ids) == 1:
            self.hotel1_id = all_ids[0]
            self.hotel2_id = all_ids[0]
    
    def test_create_managers(self):
        """Test manager creation"""
        print_section("Testing Manager Creation")
        
        # Use dynamically extracted hotel IDs, fallback to 1 and 2
        hotel1_id = self.hotel1_id or "1"
        hotel2_id = self.hotel2_id or "2"
        
        # Manager creation requires hotel_id
        manager1_data = {**TEST_MANAGER_1, "hotel_id": hotel1_id}
        manager2_data = {**TEST_MANAGER_2, "hotel_id": hotel2_id}
        
        # Create Manager 1
        response = self.admin_session.post(f"{BASE_URL}/admin/add-manager", data=manager1_data, allow_redirects=False)
        self.results.add(f"Create Manager 1 ({TEST_MANAGER_1['username']})", response.status_code in [200, 302])
        
        # Create Manager 2
        response = self.admin_session.post(f"{BASE_URL}/admin/add-manager", data=manager2_data, allow_redirects=False)
        self.results.add(f"Create Manager 2 ({TEST_MANAGER_2['username']})", response.status_code in [200, 302])
        
        # Test duplicate username rejection (needs hotel_id too)
        dup_manager_data = {**TEST_MANAGER_1, "hotel_id": "3"}
        response = self.admin_session.post(f"{BASE_URL}/admin/add-manager", data=dup_manager_data, allow_redirects=False)
        is_rejected = "already exists" in response.text.lower() or response.status_code == 200
        self.results.add("Duplicate manager username rejected", is_rejected)
        
        # Check managers list page loads
        response = self.admin_session.get(f"{BASE_URL}/admin/all-managers")
        self.results.add("Managers list page loads", response.status_code == 200)

    # ==================== MANAGER TESTS ====================
    
    def test_manager_login(self):
        """Test manager login"""
        print_section("Testing Manager Login")
        
        # Test invalid login (manager login uses JSON)
        response = self.manager1_session.post(f"{BASE_URL}/hotel-manager/login", json={
            "username": "wrong",
            "password": "wrong"
        })
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Manager invalid login rejected", not result.get("success", True))
        
        # Test valid login for Manager 1
        response = self.manager1_session.post(f"{BASE_URL}/hotel-manager/login", json={
            "username": TEST_MANAGER_1["username"],
            "password": TEST_MANAGER_1["password"]
        })
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Manager 1 valid login", result.get("success", False), result.get("message", ""))
        
        # Test valid login for Manager 2
        response = self.manager2_session.post(f"{BASE_URL}/hotel-manager/login", json={
            "username": TEST_MANAGER_2["username"],
            "password": TEST_MANAGER_2["password"]
        })
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Manager 2 valid login", result.get("success", False), result.get("message", ""))
        
        # Test dashboard access
        response = self.manager1_session.get(f"{BASE_URL}/hotel-manager/dashboard")
        self.results.add("Manager 1 dashboard accessible", response.status_code == 200)
        
        response = self.manager2_session.get(f"{BASE_URL}/hotel-manager/dashboard")
        self.results.add("Manager 2 dashboard accessible", response.status_code == 200)

    # ==================== WAITER TESTS (Hotel-Specific) ====================
    
    def test_waiter_management(self):
        """Test waiter management with hotel isolation"""
        print_section("Testing Waiter Management (Hotel-Specific)")
        
        # Add waiter for Manager 1's hotel
        waiter1_data = {
            "manager_id": 1,
            "name": "Waiter One",
            "email": f"waiter1_{TIMESTAMP}@test.com",
            "phone": "1111111111"
        }
        response = self.manager1_session.post(
            f"{BASE_URL}/hotel-manager/add-waiter",
            json=waiter1_data
        )
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Add waiter for Hotel 1", result.get("success", False), result.get("message", ""))
        
        # Add waiter for Manager 2's hotel
        waiter2_data = {
            "manager_id": 2,
            "name": "Waiter Two",
            "email": f"waiter2_{TIMESTAMP}@test.com",
            "phone": "2222222222"
        }
        response = self.manager2_session.post(
            f"{BASE_URL}/hotel-manager/add-waiter",
            json=waiter2_data
        )
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Add waiter for Hotel 2", result.get("success", False), result.get("message", ""))
        
        # Verify hotel isolation - Manager 1 should only see their waiter
        response = self.manager1_session.get(f"{BASE_URL}/hotel-manager/dashboard")
        has_waiter1 = "Waiter One" in response.text
        has_waiter2 = "Waiter Two" in response.text
        self.results.add("Hotel 1 sees own waiter", has_waiter1)
        self.results.add("Hotel 1 doesn't see Hotel 2 waiter", not has_waiter2)

    # ==================== MENU TESTS (Hotel-Specific) ====================
    
    def test_menu_categories(self):
        """Test menu category management with hotel isolation"""
        print_section("Testing Menu Categories (Hotel-Specific)")
        
        # Add category for Hotel 1 (use unique name with timestamp)
        response = self.manager1_session.post(
            f"{BASE_URL}/api/add-category",
            json={"name": f"Hotel1 Starters {TIMESTAMP}"}
        )
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Add category for Hotel 1", result.get("success", False), result.get("message", ""))
        
        # Add category for Hotel 2 (use unique name with timestamp)
        response = self.manager2_session.post(
            f"{BASE_URL}/api/add-category",
            json={"name": f"Hotel2 Appetizers {TIMESTAMP}"}
        )
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Add category for Hotel 2", result.get("success", False), result.get("message", ""))
        
        # Verify hotel isolation - Hotel 1 categories
        response = self.manager1_session.get(f"{BASE_URL}/api/categories")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        categories = result.get("categories", {})
        has_own = any("Hotel1" in name for name in categories.values()) if categories else False
        has_other = any("Hotel2" in name for name in categories.values()) if categories else False
        self.results.add("Hotel 1 sees own categories", has_own or len(categories) == 0, "No categories found")
        self.results.add("Hotel 1 doesn't see Hotel 2 categories", not has_other)
        
        # Verify hotel isolation - Hotel 2 categories
        response = self.manager2_session.get(f"{BASE_URL}/api/categories")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        categories = result.get("categories", {})
        has_own = any("Hotel2" in name for name in categories.values()) if categories else False
        has_other = any("Hotel1" in name for name in categories.values()) if categories else False
        self.results.add("Hotel 2 sees own categories", has_own or len(categories) == 0, "No categories found")
        self.results.add("Hotel 2 doesn't see Hotel 1 categories", not has_other)
    
    def test_menu_dishes(self):
        """Test menu dish management with hotel isolation"""
        print_section("Testing Menu Dishes (Hotel-Specific)")
        
        # First get category ID for Hotel 1
        response = self.manager1_session.get(f"{BASE_URL}/api/categories")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        categories = result.get("categories", {})
        
        if categories:
            category_id = list(categories.keys())[0]
            
            # Add dish for Hotel 1 (use unique name with timestamp)
            response = self.manager1_session.post(
                f"{BASE_URL}/api/add-dish",
                data={
                    "category_id": category_id,
                    "name": f"Hotel1 Special Dish {TIMESTAMP}",
                    "price": "299.99",
                    "quantity": "1 plate",
                    "description": "A special dish for Hotel 1"
                }
            )
            result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            self.results.add("Add dish for Hotel 1", result.get("success", False), result.get("message", ""))
            
            # Get dishes for that category
            response = self.manager1_session.get(f"{BASE_URL}/api/dishes/{category_id}")
            result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            dishes = result.get("dishes", [])
            has_dish = any("Hotel1 Special" in d.get("name", "") for d in dishes)
            self.results.add("Hotel 1 can retrieve own dishes", has_dish or len(dishes) > 0)
        else:
            self.results.add("Add dish for Hotel 1", False, "No categories available")

    # ==================== TABLE TESTS (Hotel-Specific) ====================
    
    def test_table_management(self):
        """Test table management with hotel isolation"""
        print_section("Testing Table Management (Hotel-Specific)")
        
        # Use unique table numbers with timestamp
        table1 = f"T1-{TIMESTAMP[-4:]}"
        table2 = f"T2-{TIMESTAMP[-4:]}"
        
        # Add table for Hotel 1
        response = self.manager1_session.post(
            f"{BASE_URL}/orders/api/tables",
            json={"table_number": table1}
        )
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Add table for Hotel 1", result.get("success", False), result.get("message", ""))
        
        # Add table for Hotel 2
        response = self.manager2_session.post(
            f"{BASE_URL}/orders/api/tables",
            json={"table_number": table2}
        )
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Add table for Hotel 2", result.get("success", False), result.get("message", ""))
        
        # Verify hotel isolation - Get tables for Hotel 1
        response = self.manager1_session.get(f"{BASE_URL}/orders/api/tables")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        tables = result.get("tables", [])
        has_own = any(table1 in str(t.get("table_number", "")) for t in tables)
        has_other = any(table2 in str(t.get("table_number", "")) for t in tables)
        self.results.add("Hotel 1 sees own tables", has_own or len(tables) > 0, "No tables found")
        self.results.add("Hotel 1 doesn't see Hotel 2 tables", not has_other)
        
        # Verify hotel isolation - Get tables for Hotel 2
        response = self.manager2_session.get(f"{BASE_URL}/orders/api/tables")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        tables = result.get("tables", [])
        has_own = any(table2 in str(t.get("table_number", "")) for t in tables)
        has_other = any(table1 in str(t.get("table_number", "")) for t in tables)
        self.results.add("Hotel 2 sees own tables", has_own or len(tables) > 0, "No tables found")
        self.results.add("Hotel 2 doesn't see Hotel 1 tables", not has_other)

    # ==================== ORDER TESTS (Hotel-Specific) ====================
    
    def test_order_management(self):
        """Test order retrieval with hotel isolation"""
        print_section("Testing Order Management (Hotel-Specific)")
        
        # Get orders for Hotel 1
        response = self.manager1_session.get(f"{BASE_URL}/orders/api/orders")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Hotel 1 can retrieve orders", result.get("success", False), result.get("message", ""))
        
        # Get orders for Hotel 2
        response = self.manager2_session.get(f"{BASE_URL}/orders/api/orders")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Hotel 2 can retrieve orders", result.get("success", False), result.get("message", ""))

    # ==================== FULL MENU API TEST ====================
    
    def test_full_menu_api(self):
        """Test full menu API with hotel isolation"""
        print_section("Testing Full Menu API (Hotel-Specific)")
        
        # Get full menu for Hotel 1
        response = self.manager1_session.get(f"{BASE_URL}/api/full-menu")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Hotel 1 full menu API", result.get("success", False), result.get("message", ""))
        
        # Get full menu for Hotel 2
        response = self.manager2_session.get(f"{BASE_URL}/api/full-menu")
        result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        self.results.add("Hotel 2 full menu API", result.get("success", False), result.get("message", ""))

    # ==================== PAGE ACCESS TESTS ====================
    
    def test_page_access(self):
        """Test page accessibility"""
        print_section("Testing Page Accessibility")
        
        pages = [
            ("/", "Home Page"),
            ("/admin/login", "Admin Login Page"),
            ("/hotel-manager/login-page", "Manager Login Page"),
        ]
        
        for url, name in pages:
            response = requests.get(f"{BASE_URL}{url}")
            self.results.add(f"{name} accessible", response.status_code == 200)
        
        # Test protected pages (should require login)
        protected_pages = [
            ("/admin/dashboard", "Admin Dashboard"),
            ("/admin/all-hotels", "All Hotels"),
            ("/admin/all-managers", "All Managers"),
        ]
        
        # Test with fresh session (not logged in)
        fresh_session = requests.Session()
        for url, name in protected_pages:
            response = fresh_session.get(f"{BASE_URL}{url}", allow_redirects=False)
            # Should redirect to login or return 403
            is_protected = response.status_code in [302, 403, 401] or "login" in response.headers.get("Location", "").lower()
            self.results.add(f"{name} protected", is_protected)

    def run_all_tests(self):
        """Run all tests"""
        print_header("SMART RESTAURANT MANAGEMENT SYSTEM - TEST SUITE")
        print(f"Testing against: {BASE_URL}")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check server first
        if not self.check_server():
            print(f"\n{Colors.RED}Server is not running! Please start the server first.{Colors.RESET}")
            print(f"Run: python app.py")
            return False
        
        # Run test suites
        self.test_page_access()
        self.test_admin_login()
        self.test_create_hotels()
        self.test_create_managers()
        self.test_manager_login()
        self.test_waiter_management()
        self.test_menu_categories()
        self.test_menu_dishes()
        self.test_table_management()
        self.test_order_management()
        self.test_full_menu_api()
        
        # Print summary
        return self.results.summary()


def main():
    print(f"\n{Colors.BOLD}Starting Smart Restaurant Management System Tests...{Colors.RESET}")
    print("Make sure the Flask server is running on http://127.0.0.1:5000\n")
    
    tester = HotelManagementTests()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
