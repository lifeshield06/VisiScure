"""
Create a test kitchen for testing authentication
"""
from kitchen.models import KitchenAuth

def create_test_kitchen():
    """Create a test kitchen with credentials"""
    print("=" * 70)
    print("CREATING TEST KITCHEN")
    print("=" * 70)
    
    result = KitchenAuth.create_kitchen(
        hotel_id=9,  # Your hotel ID
        section_name="Test Kitchen",
        username="testkitchen",
        password="test123",
        category_ids=[7, 8]  # Starters, Main Course
    )
    
    if result['success']:
        print("\n✅ Test kitchen created successfully!")
        print(f"   Kitchen ID: {result['kitchen_id']}")
        print(f"   Username: testkitchen")
        print(f"   Password: test123")
        print(f"   Categories: Starters, Main Course")
        print(f"\n🔗 Login URL: http://127.0.0.1:5000/kitchen/login")
    else:
        print(f"\n❌ Error: {result['message']}")
    
    print("=" * 70)

if __name__ == "__main__":
    create_test_kitchen()
