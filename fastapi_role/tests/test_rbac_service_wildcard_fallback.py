"""Tests for RBACService wildcard fallback functionality.

Tests for task 5.1: Validate ownership provider system works correctly
- Verify wildcard provider fallback works correctly in RBACService
- Test RBACService integration with OwnershipRegistry
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from fastapi_role import RBACService
from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.ownership import OwnershipRegistry
from fastapi_role.providers import DefaultOwnershipProvider
from tests.conftest import TestUser as User


class TestRBACServiceWildcardFallback:
    """Test RBACService wildcard provider fallback functionality."""

    @pytest.fixture
    def rbac_service(self):
        """Create RBACService with mocked dependencies."""
        config = CasbinConfig(superadmin_role="superadmin")
        with patch("casbin.Enforcer"):
            service = RBACService(config=config)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_wildcard_fallback_when_no_specific_provider(self, rbac_service):
        """Test that RBACService falls back to wildcard provider when no specific provider exists."""
        # Create a custom provider for wildcard
        class CustomWildcardProvider:
            def __init__(self, return_value):
                self.return_value = return_value
                self.call_count = 0
                
            async def check_ownership(self, user, resource_type, resource_id):
                self.call_count += 1
                return self.return_value
                
        wildcard_provider = CustomWildcardProvider(return_value=True)
        rbac_service.ownership_registry.register("*", wildcard_provider)
        
        user = User(id=1, role="user")
        
        # Check unregistered resource type - should fall back to wildcard
        result = await rbac_service.check_resource_ownership(user, "unregistered_type", 123)
        
        assert result is True
        assert wildcard_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_specific_provider_takes_precedence_over_wildcard(self, rbac_service):
        """Test that specific providers take precedence over wildcard in RBACService."""
        class SpecificProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return False  # Specific provider denies
                
        class WildcardProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return True  # Wildcard provider allows
                
        # Register both providers
        rbac_service.ownership_registry.register("*", WildcardProvider())
        rbac_service.ownership_registry.register("document", SpecificProvider())
        
        user = User(id=1, role="user")
        
        # Specific provider should be used for "document"
        result1 = await rbac_service.check_resource_ownership(user, "document", 123)
        assert result1 is False
        
        # Wildcard provider should be used for unregistered type
        result2 = await rbac_service.check_resource_ownership(user, "project", 456)
        assert result2 is True

    @pytest.mark.asyncio
    async def test_no_provider_returns_false(self, rbac_service):
        """Test that RBACService returns False when no provider is registered."""
        # Clear all providers (including default wildcard)
        rbac_service.ownership_registry = OwnershipRegistry(default_allow=False)
        
        user = User(id=1, role="user")
        
        # No providers registered - should return False
        result = await rbac_service.check_resource_ownership(user, "unknown", 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_wildcard_provider_with_different_resource_types(self, rbac_service):
        """Test wildcard provider handling different resource types."""
        class ConditionalWildcardProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                # Allow access based on resource_id pattern
                return resource_id % 2 == 0  # Allow even IDs
                
        rbac_service.ownership_registry.register("*", ConditionalWildcardProvider())
        
        user = User(id=1, role="user")
        
        # Test different resource types with even/odd IDs
        result1 = await rbac_service.check_resource_ownership(user, "document", 2)  # Even
        result2 = await rbac_service.check_resource_ownership(user, "project", 3)   # Odd
        result3 = await rbac_service.check_resource_ownership(user, "task", 4)      # Even
        result4 = await rbac_service.check_resource_ownership(user, "file", 5)      # Odd
        
        assert result1 is True
        assert result2 is False
        assert result3 is True
        assert result4 is False

    @pytest.mark.asyncio
    async def test_wildcard_provider_error_handling(self, rbac_service):
        """Test error handling in wildcard provider."""
        class ErrorProneWildcardProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                if resource_id == 999:
                    raise ValueError("Wildcard provider error")
                return True
                
        rbac_service.ownership_registry.register("*", ErrorProneWildcardProvider())
        
        user = User(id=1, role="user")
        
        # Normal operation should work
        result = await rbac_service.check_resource_ownership(user, "document", 123)
        assert result is True
        
        # Error should be propagated
        with pytest.raises(ValueError, match="Wildcard provider error"):
            await rbac_service.check_resource_ownership(user, "document", 999)

    @pytest.mark.asyncio
    async def test_multiple_resource_types_with_mixed_providers(self, rbac_service):
        """Test multiple resource types with mix of specific and wildcard providers."""
        class DocumentProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return user.id == resource_id  # User owns document with matching ID
                
        class ProjectProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return resource_id < 100  # Only allow projects with ID < 100
                
        class WildcardProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return user.role == "admin"  # Only admins can access other resources
                
        # Register providers
        rbac_service.ownership_registry.register("document", DocumentProvider())
        rbac_service.ownership_registry.register("project", ProjectProvider())
        rbac_service.ownership_registry.register("*", WildcardProvider())
        
        regular_user = User(id=5, role="user")
        admin_user = User(id=10, role="admin")
        
        # Test document access (specific provider)
        assert await rbac_service.check_resource_ownership(regular_user, "document", 5) is True
        assert await rbac_service.check_resource_ownership(regular_user, "document", 10) is False
        assert await rbac_service.check_resource_ownership(admin_user, "document", 10) is True
        
        # Test project access (specific provider)
        assert await rbac_service.check_resource_ownership(regular_user, "project", 50) is True
        assert await rbac_service.check_resource_ownership(regular_user, "project", 150) is False
        assert await rbac_service.check_resource_ownership(admin_user, "project", 150) is False  # Specific provider used
        
        # Test other resource types (wildcard provider)
        assert await rbac_service.check_resource_ownership(regular_user, "task", 123) is False
        assert await rbac_service.check_resource_ownership(admin_user, "task", 123) is True
        assert await rbac_service.check_resource_ownership(regular_user, "file", 456) is False
        assert await rbac_service.check_resource_ownership(admin_user, "file", 456) is True

    @pytest.mark.asyncio
    async def test_default_wildcard_provider_behavior(self, rbac_service):
        """Test the default wildcard provider behavior in RBACService."""
        # RBACService should register a default wildcard provider
        assert rbac_service.ownership_registry.has_provider("*")
        
        superadmin = User(id=1, role="superadmin")
        regular_user = User(id=2, role="user")
        
        # Default wildcard provider should allow superadmin and deny others
        result1 = await rbac_service.check_resource_ownership(superadmin, "unknown", 123)
        result2 = await rbac_service.check_resource_ownership(regular_user, "unknown", 123)
        
        assert result1 is True   # Superadmin allowed
        assert result2 is False  # Regular user denied

    @pytest.mark.asyncio
    async def test_wildcard_provider_replacement(self, rbac_service):
        """Test replacing the default wildcard provider."""
        class CustomWildcardProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return user.role in ["admin", "manager"]  # Allow admin and manager
                
        # Replace default wildcard provider
        rbac_service.ownership_registry.register("*", CustomWildcardProvider())
        
        superadmin = User(id=1, role="superadmin")
        admin = User(id=2, role="admin")
        manager = User(id=3, role="manager")
        user = User(id=4, role="user")
        
        # Test with custom wildcard provider
        result1 = await rbac_service.check_resource_ownership(superadmin, "unknown", 123)
        result2 = await rbac_service.check_resource_ownership(admin, "unknown", 123)
        result3 = await rbac_service.check_resource_ownership(manager, "unknown", 123)
        result4 = await rbac_service.check_resource_ownership(user, "unknown", 123)
        
        assert result1 is False  # Superadmin no longer has special treatment
        assert result2 is True   # Admin allowed
        assert result3 is True   # Manager allowed
        assert result4 is False  # Regular user denied


class TestRBACServiceOwnershipIntegration:
    """Test RBACService integration with ownership system."""

    @pytest.fixture
    def rbac_service(self):
        """Create RBACService with mocked dependencies."""
        config = CasbinConfig(superadmin_role="superadmin")
        with patch("casbin.Enforcer"):
            service = RBACService(config=config)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_can_access_with_ownership_check(self, rbac_service):
        """Test can_access method with ownership checking."""
        from fastapi_role.core.resource import ResourceRef
        
        # Mock permission check to return True
        rbac_service.check_permission = AsyncMock(return_value=True)
        
        # Register custom ownership provider
        class CustomOwnershipProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return resource_id == user.id  # User owns resource with matching ID
                
        rbac_service.ownership_registry.register("document", CustomOwnershipProvider())
        
        user = User(id=5, role="user")
        resource_owned = ResourceRef("document", 5)
        resource_not_owned = ResourceRef("document", 10)
        
        # Test access to owned resource
        result1 = await rbac_service.can_access(user, resource_owned, "read")
        assert result1 is True
        
        # Test access to non-owned resource
        result2 = await rbac_service.can_access(user, resource_not_owned, "read")
        assert result2 is False

    @pytest.mark.asyncio
    async def test_can_access_without_ownership_provider(self, rbac_service):
        """Test can_access method when no ownership provider is registered."""
        from fastapi_role.core.resource import ResourceRef
        
        # Mock permission check to return True
        rbac_service.check_permission = AsyncMock(return_value=True)
        
        # Clear ownership providers
        rbac_service.ownership_registry = OwnershipRegistry(default_allow=False)
        
        user = User(id=5, role="user")
        resource = ResourceRef("unknown_type", 123)
        
        # Should still work if no ownership provider exists
        # (ownership check is skipped when no provider is registered)
        result = await rbac_service.can_access(user, resource, "read")
        assert result is True  # Permission allowed, no ownership check needed

    @pytest.mark.asyncio
    async def test_can_access_with_wildcard_ownership(self, rbac_service):
        """Test can_access method with wildcard ownership provider."""
        from fastapi_role.core.resource import ResourceRef
        
        # Mock permission check to return True
        rbac_service.check_permission = AsyncMock(return_value=True)
        
        # Register wildcard ownership provider
        class WildcardOwnershipProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return user.role == "admin"  # Only admins can own anything
                
        rbac_service.ownership_registry.register("*", WildcardOwnershipProvider())
        
        admin = User(id=1, role="admin")
        user = User(id=2, role="user")
        resource = ResourceRef("any_type", 123)
        
        # Test access with admin (should pass ownership)
        result1 = await rbac_service.can_access(admin, resource, "read")
        assert result1 is True
        
        # Test access with regular user (should fail ownership)
        result2 = await rbac_service.can_access(user, resource, "read")
        assert result2 is False