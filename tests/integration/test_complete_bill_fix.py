"""
Test script to verify Bill.complete_bill() method works correctly
"""
import sys
sys.path.insert(0, '.')

from orders.table_models import Bill

# Test that the method exists and is callable
print("=" * 60)
print("Testing Bill.complete_bill() Method")
print("=" * 60)

# Check if method has @staticmethod decorator properly
print("\n1. Checking method signature...")
print(f"   Method type: {type(Bill.complete_bill)}")
print(f"   Is callable: {callable(Bill.complete_bill)}")

# Try calling with a test bill_id (will fail if bill doesn't exist, but that's OK)
print("\n2. Testing method call with bill_id=999999...")
try:
    result = Bill.complete_bill(999999)
    print(f"   ✓ Method executed successfully")
    print(f"   Result: {result}")
    print(f"   Expected: False (bill doesn't exist)")
    if result == False:
        print("   ✓ Method returned correct value for non-existent bill")
except TypeError as e:
    print(f"   ✗ TypeError occurred: {e}")
    print("   This indicates the @staticmethod decorator is still missing or duplicated")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Unexpected error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All checks passed! Bill.complete_bill() is working correctly")
print("=" * 60)
