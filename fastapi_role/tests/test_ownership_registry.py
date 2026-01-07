"""Tests for ownership registry and providers.

Tests the OwnershipProvider protocol, OwnershipRegistry, and DefaultOwnershipProvider.
"""

from unittest.mock import AsyncMock

import pytest

from fastapi_role.core.ownership import OwnershipRegistry
from fastapi_role.providers import DefaultOwnershipProvider
from tests.conftest import TestUser as User


class MockOwnershipProvider:
    """Mock ownership provider for testing."""

    def __init__(self, return_value: bool = True):
        self.return_value = return_value
        self.check_ownership = AsyncMock(return_value=return_value)


class TestOwnershipRegistry:
    """Test OwnershipRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry initializes with correct defaults."""
        registry = OwnershipRegistry(default_allow=False)
        assert registry._default_allow is False

        registry2 = OwnershipRegistry(default_allow=True)
        assert registry2._default_allow is True

    def test_register_provider(self):
        """Test registering a provider for a resource type."""
        registry = OwnershipRegistry()
        provider = MockOwnershipProvider()

        registry.register("order", provider)
        assert registry.has_provider("order")

    def test_has_provider(self):
        """Test checking if provider is registered."""
        registry = OwnershipRegistry()
        provider = MockOwnershipProvider()

        assert not registry.has_provider("order")
        registry.register("order", provider)
        assert registry.has_provider("order")

    @pytest.mark.asyncio
    async def test_check_with_registered_provider(self):
        """Test ownership check uses registered provider."""
        registry = OwnershipRegistry()
        provider = MockOwnershipProvider(return_value=True)
        registry.register("order", provider)

        user = User(id=1, role="customer")
        result = await registry.check(user, "order", 123)

        assert result is True
        provider.check_ownership.assert_called_once_with(user, "order", 123)

    @pytest.mark.asyncio
    async def test_check_without_provider_default_deny(self):
        """Test ownership check without provider uses default_allow=False."""
        registry = OwnershipRegistry(default_allow=False)
        user = User(id=1, role="customer")

        result = await registry.check(user, "unregistered", 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_without_provider_default_allow(self):
        """Test ownership check without provider uses default_allow=True."""
        registry = OwnershipRegistry(default_allow=True)
        user = User(id=1, role="customer")

        result = await registry.check(user, "unregistered", 123)
        assert result is True

    def test_unregister_provider(self):
        """Test unregistering a provider."""
        registry = OwnershipRegistry()
        provider = MockOwnershipProvider()

        registry.register("order", provider)
        assert registry.has_provider("order")

        removed = registry.unregister("order")
        assert removed is provider
        assert not registry.has_provider("order")

    def test_unregister_nonexistent_provider(self):
        """Test unregistering a non-existent provider returns None."""
        registry = OwnershipRegistry()
        result = registry.unregister("nonexistent")
        assert result is None


class TestDefaultOwnershipProvider:
    """Test DefaultOwnershipProvider functionality."""

    @pytest.mark.asyncio
    async def test_superadmin_bypass(self):
        """Test superadmin role bypasses ownership checks."""
        provider = DefaultOwnershipProvider(superadmin_role="superadmin")
        user = User(id=1, role="superadmin")

        result = await provider.check_ownership(user, "order", 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_non_superadmin_default_deny(self):
        """Test non-superadmin with default_allow=False is denied."""
        provider = DefaultOwnershipProvider(
            superadmin_role="superadmin", default_allow=False
        )
        user = User(id=1, role="customer")

        result = await provider.check_ownership(user, "order", 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_non_superadmin_default_allow(self):
        """Test non-superadmin with default_allow=True is allowed."""
        provider = DefaultOwnershipProvider(
            superadmin_role="superadmin", default_allow=True
        )
        user = User(id=1, role="customer")

        result = await provider.check_ownership(user, "order", 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_allowed_roles(self):
        """Test allowed_roles grants access."""
        provider = DefaultOwnershipProvider(
            superadmin_role="superadmin",
            default_allow=False,
            allowed_roles={"manager", "admin"},
        )
        
        manager = User(id=1, role="manager")
        customer = User(id=2, role="customer")

        assert await provider.check_ownership(manager, "order", 123) is True
        assert await provider.check_ownership(customer, "order", 123) is False

    @pytest.mark.asyncio
    async def test_custom_superadmin_role(self):
        """Test custom superadmin role name."""
        provider = DefaultOwnershipProvider(superadmin_role="root")
        
        root_user = User(id=1, role="root")
        admin_user = User(id=2, role="superadmin")

        assert await provider.check_ownership(root_user, "order", 123) is True
        assert await provider.check_ownership(admin_user, "order", 123) is False


class TestRBACServiceOwnershipIntegration:
    """Test RBACService integration with ownership registry."""

    @pytest.fixture
    def rbac_service(self):
        """Create RBACService with mocked dependencies."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi_role import RBACService

        from fastapi_role.core.config import CasbinConfig
        config = CasbinConfig(superadmin_role="superadmin")
        with patch("casbin.Enforcer"):
            service = RBACService(config=config)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_service_has_ownership_registry(self, rbac_service):
        """Test RBACService initializes with ownership registry."""
        assert hasattr(rbac_service, "ownership_registry")
        assert isinstance(rbac_service.ownership_registry, OwnershipRegistry)

    @pytest.mark.asyncio
    async def test_service_registers_wildcard_provider(self, rbac_service):
        """Test RBACService registers wildcard (*) provider by default."""
        assert rbac_service.ownership_registry.has_provider("*")

    @pytest.mark.asyncio
    async def test_check_resource_ownership_uses_registry(self, rbac_service):
        """Test check_resource_ownership delegates to registry."""
        user = User(id=1, role="superadmin")
        
        # Superadmin should pass via default provider
        result = await rbac_service.check_resource_ownership(user, "order", 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_ownership_custom_provider(self, rbac_service):
        """Test check_resource_ownership uses custom registered provider."""
        custom_provider = MockOwnershipProvider(return_value=True)
        rbac_service.ownership_registry.register("custom_resource", custom_provider)

        user = User(id=1, role="customer")
        result = await rbac_service.check_resource_ownership(user, "custom_resource", 456)

        assert result is True
        custom_provider.check_ownership.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_resource_ownership_fallback_to_wildcard(self, rbac_service):
        """Test check_resource_ownership falls back to wildcard provider."""
        user = User(id=1, role="customer")
        
        # No specific provider for "unregistered", should fall back to wildcard
        result = await rbac_service.check_resource_ownership(user, "unregistered", 789)
        
        # Default wildcard provider denies non-superadmin
        assert result is False
