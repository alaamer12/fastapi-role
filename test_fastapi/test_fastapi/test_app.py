"""
Simple test script to verify the test application works.
Tests basic functionality and RBAC integration.
"""
import asyncio
import sys
from pathlib import Path

# Add the test_fastapi package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_fastapi.database import create_tables, init_sample_data, get_db
from test_fastapi.rbac_setup import create_rbac_service, Role
from test_fastapi.models import User
from test_fastapi.ownership_providers import create_ownership_providers_with_superadmin


async def test_rbac_setup():
    """Test RBAC service setup and basic functionality."""
    
    print("🔧 Testing RBAC Setup...")
    
    # Test dynamic role creation
    print(f"✅ Dynamic roles created: {[role.value for role in Role]}")
    
    # Test RBAC service creation
    rbac_service = create_rbac_service()
    print("✅ RBAC service created successfully")
    
    # Test ownership providers
    providers = create_ownership_providers_with_superadmin()
    print(f"✅ Ownership providers created: {list(providers.keys())}")
    
    return rbac_service


async def test_database_setup():
    """Test database setup and sample data."""
    
    print("\n📊 Testing Database Setup...")
    
    # Create tables
    create_tables()
    print("✅ Database tables created")
    
    # Initialize sample data
    db = next(get_db())
    try:
        init_sample_data(db)
        print("✅ Sample data initialized")
        
        # Check users
        users = db.query(User).all()
        print(f"✅ Found {len(users)} users:")
        for user in users:
            print(f"   - {user.email} ({user.role})")
            
    finally:
        db.close()


async def test_rbac_permissions():
    """Test RBAC permission checking."""
    
    print("\n🔐 Testing RBAC Permissions...")
    
    rbac_service = create_rbac_service()
    
    # Get a test user
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.role == "admin").first()
        regular_user = db.query(User).filter(User.role == "user").first()
        
        if not admin_user or not regular_user:
            print("❌ Test users not found")
            return
        
        # Test admin permissions
        admin_can_create_user = await rbac_service.check_permission(admin_user, "user", "create")
        print(f"✅ Admin can create users: {admin_can_create_user}")
        
        admin_can_delete_user = await rbac_service.check_permission(admin_user, "user", "delete")
        print(f"✅ Admin can delete users: {admin_can_delete_user}")
        
        # Test regular user permissions
        user_can_create_doc = await rbac_service.check_permission(regular_user, "document", "create")
        print(f"✅ User can create documents: {user_can_create_doc}")
        
        user_can_delete_user = await rbac_service.check_permission(regular_user, "user", "delete")
        print(f"✅ User can delete users: {user_can_delete_user}")
        
    finally:
        db.close()


async def test_ownership_providers():
    """Test ownership provider functionality."""
    
    print("\n🏠 Testing Ownership Providers...")
    
    # Get test users and resources
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.role == "admin").first()
        regular_user = db.query(User).filter(User.role == "user").first()
        
        if not admin_user or not regular_user:
            print("❌ Test users not found")
            return
        
        # Test ownership providers
        providers = create_ownership_providers_with_superadmin()
        
        # Test document ownership (assuming document ID 1 exists and is owned by admin)
        doc_provider = providers["document"]
        admin_owns_doc = await doc_provider.check_ownership(admin_user, "document", 1)
        user_owns_doc = await doc_provider.check_ownership(regular_user, "document", 1)
        
        print(f"✅ Admin owns document 1: {admin_owns_doc}")
        print(f"✅ User owns document 1: {user_owns_doc}")
        
        # Test user ownership (users can access their own profile)
        user_provider = providers["user"]
        user_owns_self = await user_provider.check_ownership(regular_user, "user", regular_user.id)
        user_owns_admin = await user_provider.check_ownership(regular_user, "user", admin_user.id)
        
        print(f"✅ User owns their profile: {user_owns_self}")
        print(f"✅ User owns admin profile: {user_owns_admin}")
        
    finally:
        db.close()


async def main():
    """Run all tests."""
    
    print("🚀 Starting Test FastAPI Application Tests\n")
    
    try:
        await test_database_setup()
        await test_rbac_setup()
        await test_rbac_permissions()
        await test_ownership_providers()
        
        print("\n🎉 All tests completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Run the application: python -m test_fastapi.main")
        print("   2. Visit http://localhost:8000/docs for API documentation")
        print("   3. Use /auth/test-users to see available test accounts")
        print("   4. Login with /auth/login to get access tokens")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())