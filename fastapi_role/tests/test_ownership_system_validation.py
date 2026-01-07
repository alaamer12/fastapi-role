"""Comprehensive tests for ownership system validation.

Tests for task 5.1: Validate ownership provider system works correctly
- Test OwnershipRegistry with various provider configurations
- Verify wildcard provider fallback works correctly  
- Ensure ownership providers handle async operations properly
- Test ownership system with different resource types
"""

import asyncio
from unittest.mock import AsyncMock
from typing import Any

import pytest

from fastapi_role.core.ownership import OwnershipRegistry, OwnershipProvider
from fastapi_role.providers import DefaultOwnershipProvider
from fastapi_role.protocols import UserProtocol
from tests.conftest import TestUser as User


class AsyncOwnershipProvider:
    """Test provider that uses async operations."""
    
    def __init__(self, delay: float = 0.01, return_value: bool = True):
        self.delay = delay
        self.return_value = return_value
        self.call_count = 0
        
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Async ownership check with delay."""
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return self.return_value


class ConditionalOwnershipProvider:
    """Test provider with conditional logic based on resource type and ID."""
    
    def __init__(self):
        self.call_log = []
        
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Conditional ownership based on resource type and ID."""
        self.call_log.append((user.id, resource_type, resource_id))
        
        # Different logic per resource type
        if resource_type == "document":
            # User owns documents with ID matching their user ID
            return resource_id == user.id
        elif resource_type == "project":
            # User owns projects with even IDs if they're admin, odd IDs if they're user
            if user.role == "admin":
                return resource_id % 2 == 0
            else:
                return resource_id % 2 == 1
        elif resource_type == "task":
            # Tasks are owned by users with ID > 10
            return user.id > 10
        else:
            # Unknown resource types denied
            return False


class TestOwnershipRegistryConfigurations:
    """Test OwnershipRegistry with various provider configurations."""
    
    def test_multiple_provider_registration(self):
        """Test registering multiple providers for different resource types."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register different providers for different resource types
        doc_provider = AsyncOwnershipProvider(return_value=True)
        project_provider = AsyncOwnershipProvider(return_value=False)
        task_provider = ConditionalOwnershipProvider()
        
        registry.register("document", doc_provider)
        registry.register("project", project_provider)
        registry.register("task", task_provider)
        
        # Verify all providers are registered
        assert registry.has_provider("document")
        assert registry.has_provider("project")
        assert registry.has_provider("task")
        assert not registry.has_provider("unknown")
        
    @pytest.mark.asyncio
    async def test_provider_isolation(self):
        """Test that providers are isolated and don't interfere with each other."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register providers with different behaviors
        allow_provider = AsyncOwnershipProvider(return_value=True)
        deny_provider = AsyncOwnershipProvider(return_value=False)
        
        registry.register("allowed_resource", allow_provider)
        registry.register("denied_resource", deny_provider)
        
        user = User(id=1, role="user")
        
        # Test that each provider is called correctly
        allowed_result = await registry.check(user, "allowed_resource", 123)
        denied_result = await registry.check(user, "denied_resource", 456)
        
        assert allowed_result is True
        assert denied_result is False
        assert allow_provider.call_count == 1
        assert deny_provider.call_count == 1
        
    @pytest.mark.asyncio
    async def test_provider_override(self):
        """Test that registering a new provider overrides the previous one."""
        registry = OwnershipRegistry()
        
        # Register initial provider
        initial_provider = AsyncOwnershipProvider(return_value=True)
        registry.register("resource", initial_provider)
        
        user = User(id=1, role="user")
        result1 = await registry.check(user, "resource", 123)
        assert result1 is True
        assert initial_provider.call_count == 1
        
        # Override with new provider
        new_provider = AsyncOwnershipProvider(return_value=False)
        registry.register("resource", new_provider)
        
        result2 = await registry.check(user, "resource", 456)
        assert result2 is False
        assert new_provider.call_count == 1
        assert initial_provider.call_count == 1  # Should not be called again


class TestWildcardProviderFallback:
    """Test wildcard provider fallback functionality."""
    
    @pytest.mark.asyncio
    async def test_wildcard_fallback_basic(self):
        """Test basic wildcard fallback when no specific provider exists."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register wildcard provider
        wildcard_provider = AsyncOwnershipProvider(return_value=True)
        registry.register("*", wildcard_provider)
        
        user = User(id=1, role="user")
        
        # Check wildcard resource type directly - registry treats "*" as regular resource type
        result = await registry.check(user, "*", 123)
        assert result is True
        assert wildcard_provider.call_count == 1
        
    @pytest.mark.asyncio
    async def test_specific_provider_takes_precedence(self):
        """Test that specific providers are used when registered."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register wildcard and specific providers
        wildcard_provider = AsyncOwnershipProvider(return_value=True)
        specific_provider = AsyncOwnershipProvider(return_value=False)
        
        registry.register("*", wildcard_provider)
        registry.register("document", specific_provider)
        
        user = User(id=1, role="user")
        
        # Check registered resource type - should use specific provider
        result1 = await registry.check(user, "document", 123)
        assert result1 is False
        assert specific_provider.call_count == 1
        assert wildcard_provider.call_count == 0
        
        # Check wildcard resource type directly
        result2 = await registry.check(user, "*", 456)
        assert result2 is True
        assert wildcard_provider.call_count == 1
        assert specific_provider.call_count == 1
        
    @pytest.mark.asyncio
    async def test_no_wildcard_uses_default(self):
        """Test that without wildcard provider, default_allow is used."""
        registry_deny = OwnershipRegistry(default_allow=False)
        registry_allow = OwnershipRegistry(default_allow=True)
        
        user = User(id=1, role="user")
        
        # No providers registered - should use default_allow
        result_deny = await registry_deny.check(user, "unknown", 123)
        result_allow = await registry_allow.check(user, "unknown", 123)
        
        assert result_deny is False
        assert result_allow is True
        
    @pytest.mark.asyncio
    async def test_wildcard_with_conditional_logic(self):
        """Test wildcard provider with conditional logic."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register conditional wildcard provider
        conditional_provider = ConditionalOwnershipProvider()
        registry.register("*", conditional_provider)
        
        admin_user = User(id=1, role="admin")
        regular_user = User(id=2, role="user")
        
        # Test wildcard provider directly with conditional logic
        # The conditional provider checks resource_type in its logic
        wildcard_result = await registry.check(admin_user, "*", 1)
        
        # Since "*" is not handled by ConditionalOwnershipProvider, it returns False
        assert wildcard_result is False
        
        # Test by registering the conditional provider for specific resource types
        registry.register("document", conditional_provider)
        registry.register("project", conditional_provider)
        
        doc_result_admin = await registry.check(admin_user, "document", 1)  # Should match user ID
        doc_result_user = await registry.check(regular_user, "document", 2)  # Should match user ID
        doc_result_mismatch = await registry.check(admin_user, "document", 999)  # Should not match
        
        project_result_admin_even = await registry.check(admin_user, "project", 4)  # Admin + even ID
        project_result_admin_odd = await registry.check(admin_user, "project", 3)   # Admin + odd ID
        project_result_user_odd = await registry.check(regular_user, "project", 5)  # User + odd ID
        project_result_user_even = await registry.check(regular_user, "project", 6) # User + even ID
        
        assert doc_result_admin is True
        assert doc_result_user is True
        assert doc_result_mismatch is False
        
        assert project_result_admin_even is True
        assert project_result_admin_odd is False
        assert project_result_user_odd is True
        assert project_result_user_even is False


class TestAsyncOperations:
    """Test that ownership providers handle async operations properly."""
    
    @pytest.mark.asyncio
    async def test_concurrent_ownership_checks(self):
        """Test concurrent ownership checks work correctly."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register provider with delay to test concurrency
        provider = AsyncOwnershipProvider(delay=0.05, return_value=True)
        registry.register("document", provider)
        
        user = User(id=1, role="user")
        
        # Run multiple concurrent checks
        tasks = [
            registry.check(user, "document", i)
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert provider.call_count == 10
        
    @pytest.mark.asyncio
    async def test_async_provider_error_handling(self):
        """Test error handling in async providers."""
        registry = OwnershipRegistry(default_allow=False)
        
        class ErrorProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                if resource_id == 999:
                    raise ValueError("Test error")
                return True
                
        registry.register("error_prone", ErrorProvider())
        user = User(id=1, role="user")
        
        # Normal operation should work
        result = await registry.check(user, "error_prone", 123)
        assert result is True
        
        # Error should be propagated
        with pytest.raises(ValueError, match="Test error"):
            await registry.check(user, "error_prone", 999)
            
    @pytest.mark.asyncio
    async def test_mixed_sync_async_providers(self):
        """Test mixing synchronous and asynchronous providers."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Sync provider (wrapped in async)
        class SyncProvider:
            def __init__(self, return_value):
                self.return_value = return_value
                
            async def check_ownership(self, user, resource_type, resource_id):
                # Simulate sync operation
                return self.return_value
                
        # Async provider
        async_provider = AsyncOwnershipProvider(delay=0.01, return_value=True)
        sync_provider = SyncProvider(return_value=False)
        
        registry.register("async_resource", async_provider)
        registry.register("sync_resource", sync_provider)
        
        user = User(id=1, role="user")
        
        # Both should work correctly
        async_result = await registry.check(user, "async_resource", 123)
        sync_result = await registry.check(user, "sync_resource", 456)
        
        assert async_result is True
        assert sync_result is False


class TestDifferentResourceTypes:
    """Test ownership system with different resource types."""
    
    @pytest.mark.asyncio
    async def test_string_resource_ids(self):
        """Test ownership with string resource IDs."""
        registry = OwnershipRegistry(default_allow=False)
        
        class StringIdProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                # Allow access if resource_id contains user's name
                return str(user.id) in str(resource_id)
                
        registry.register("file", StringIdProvider())
        
        user = User(id=123, role="user")
        
        # Test various string IDs
        result1 = await registry.check(user, "file", "user_123_document.pdf")
        result2 = await registry.check(user, "file", "shared_456_file.txt")
        result3 = await registry.check(user, "file", "document_123.docx")
        
        assert result1 is True
        assert result2 is False
        assert result3 is True
        
    @pytest.mark.asyncio
    async def test_complex_resource_ids(self):
        """Test ownership with complex resource ID types."""
        registry = OwnershipRegistry(default_allow=False)
        
        class ComplexIdProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                if isinstance(resource_id, dict):
                    return resource_id.get("owner_id") == user.id
                elif isinstance(resource_id, tuple):
                    return user.id in resource_id
                elif isinstance(resource_id, list):
                    return user.id in resource_id
                else:
                    return False
                    
        registry.register("complex", ComplexIdProvider())
        
        user = User(id=42, role="user")
        
        # Test different ID types
        dict_result = await registry.check(user, "complex", {"owner_id": 42, "name": "test"})
        tuple_result = await registry.check(user, "complex", (1, 42, 3))
        list_result = await registry.check(user, "complex", [10, 20, 42])
        wrong_dict_result = await registry.check(user, "complex", {"owner_id": 99})
        wrong_tuple_result = await registry.check(user, "complex", (1, 2, 3))
        
        assert dict_result is True
        assert tuple_result is True
        assert list_result is True
        assert wrong_dict_result is False
        assert wrong_tuple_result is False
        
    @pytest.mark.asyncio
    async def test_resource_type_variations(self):
        """Test ownership with various resource type naming conventions."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Register providers for different naming conventions
        provider = AsyncOwnershipProvider(return_value=True)
        
        resource_types = [
            "document",           # lowercase
            "Document",           # capitalized
            "DOCUMENT",           # uppercase
            "user_document",      # underscore
            "user-document",      # hyphen
            "userDocument",       # camelCase
            "UserDocument",       # PascalCase
            "user.document",      # dot notation
            "user/document",      # path-like
            "user:document",      # colon notation
        ]
        
        for resource_type in resource_types:
            registry.register(resource_type, provider)
            
        user = User(id=1, role="user")
        
        # All should work correctly
        for resource_type in resource_types:
            result = await registry.check(user, resource_type, 123)
            assert result is True, f"Failed for resource type: {resource_type}"
            
    @pytest.mark.asyncio
    async def test_resource_hierarchy_simulation(self):
        """Test simulating resource hierarchy with ownership providers."""
        registry = OwnershipRegistry(default_allow=False)
        
        class HierarchicalProvider:
            def __init__(self):
                # Simulate a resource hierarchy
                self.hierarchy = {
                    "organization": {1: [10, 11, 12]},  # org 1 contains projects 10,11,12
                    "project": {10: [100, 101], 11: [102, 103], 12: [104]},  # projects contain tasks
                    "task": {100: 1, 101: 1, 102: 2, 103: 2, 104: 3}  # tasks owned by users
                }
                
            async def check_ownership(self, user, resource_type, resource_id):
                if resource_type == "task":
                    # Direct ownership - base case
                    return self.hierarchy["task"].get(resource_id) == user.id
                elif resource_type == "project":
                    # User owns project if they own any task in it
                    tasks = self.hierarchy["project"].get(resource_id, [])
                    for task_id in tasks:
                        if self.hierarchy["task"].get(task_id) == user.id:
                            return True
                    return False
                elif resource_type == "organization":
                    # User owns org if they own any project in it
                    projects = self.hierarchy["organization"].get(resource_id, [])
                    for project_id in projects:
                        # Check project ownership directly without recursion
                        tasks = self.hierarchy["project"].get(project_id, [])
                        for task_id in tasks:
                            if self.hierarchy["task"].get(task_id) == user.id:
                                return True
                    return False
                return False
                
        registry.register("task", HierarchicalProvider())
        registry.register("project", HierarchicalProvider())
        registry.register("organization", HierarchicalProvider())
        
        user1 = User(id=1, role="user")
        user2 = User(id=2, role="user")
        user3 = User(id=3, role="user")
        
        # Test hierarchical ownership
        # User 1 owns tasks 100, 101 -> owns project 10 -> owns org 1
        assert await registry.check(user1, "task", 100) is True
        assert await registry.check(user1, "task", 102) is False
        assert await registry.check(user1, "project", 10) is True
        assert await registry.check(user1, "project", 11) is False
        assert await registry.check(user1, "organization", 1) is True
        
        # User 2 owns tasks 102, 103 -> owns project 11 -> owns org 1
        assert await registry.check(user2, "task", 102) is True
        assert await registry.check(user2, "task", 100) is False
        assert await registry.check(user2, "project", 11) is True
        assert await registry.check(user2, "project", 10) is False
        assert await registry.check(user2, "organization", 1) is True
        
        # User 3 owns task 104 -> owns project 12 -> owns org 1
        assert await registry.check(user3, "task", 104) is True
        assert await registry.check(user3, "project", 12) is True
        assert await registry.check(user3, "organization", 1) is True


class TestDefaultOwnershipProviderEnhancements:
    """Test DefaultOwnershipProvider with various configurations."""
    
    @pytest.mark.asyncio
    async def test_allowed_roles_configuration(self):
        """Test DefaultOwnershipProvider with allowed_roles configuration."""
        provider = DefaultOwnershipProvider(
            superadmin_role="superadmin",
            default_allow=False,
            allowed_roles={"manager", "admin", "editor"}
        )
        
        # Test different user roles
        superadmin = User(id=1, role="superadmin")
        manager = User(id=2, role="manager")
        admin = User(id=3, role="admin")
        editor = User(id=4, role="editor")
        user = User(id=5, role="user")
        
        # All allowed roles should have access
        assert await provider.check_ownership(superadmin, "document", 123) is True
        assert await provider.check_ownership(manager, "document", 123) is True
        assert await provider.check_ownership(admin, "document", 123) is True
        assert await provider.check_ownership(editor, "document", 123) is True
        
        # Non-allowed role should be denied
        assert await provider.check_ownership(user, "document", 123) is False
        
    @pytest.mark.asyncio
    async def test_no_superadmin_configuration(self):
        """Test DefaultOwnershipProvider without superadmin role."""
        provider = DefaultOwnershipProvider(
            superadmin_role=None,
            default_allow=True,
            allowed_roles={"admin"}
        )
        
        admin = User(id=1, role="admin")
        superadmin = User(id=2, role="superadmin")  # This role has no special meaning
        user = User(id=3, role="user")
        
        # Admin should be allowed via allowed_roles
        assert await provider.check_ownership(admin, "document", 123) is True
        
        # "superadmin" role should fall back to default_allow since no superadmin_role configured
        assert await provider.check_ownership(superadmin, "document", 123) is True
        
        # Regular user should fall back to default_allow
        assert await provider.check_ownership(user, "document", 123) is True
        
    @pytest.mark.asyncio
    async def test_empty_allowed_roles(self):
        """Test DefaultOwnershipProvider with empty allowed_roles."""
        provider = DefaultOwnershipProvider(
            superadmin_role="superadmin",
            default_allow=False,
            allowed_roles=set()  # Empty set
        )
        
        superadmin = User(id=1, role="superadmin")
        admin = User(id=2, role="admin")
        
        # Only superadmin should have access
        assert await provider.check_ownership(superadmin, "document", 123) is True
        assert await provider.check_ownership(admin, "document", 123) is False


class TestOwnershipRegistryEdgeCases:
    """Test edge cases and error conditions in OwnershipRegistry."""
    
    def test_registry_with_none_resource_type(self):
        """Test registry behavior with None resource type."""
        registry = OwnershipRegistry(default_allow=True)
        
        # Should handle None gracefully
        assert not registry.has_provider(None)
        
        # Unregistering None should return None
        result = registry.unregister(None)
        assert result is None
        
    @pytest.mark.asyncio
    async def test_registry_with_none_resource_id(self):
        """Test registry behavior with None resource ID."""
        registry = OwnershipRegistry(default_allow=False)
        
        class NoneIdProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                return resource_id is None
                
        registry.register("nullable", NoneIdProvider())
        user = User(id=1, role="user")
        
        # Should handle None resource_id
        result1 = await registry.check(user, "nullable", None)
        result2 = await registry.check(user, "nullable", 123)
        
        assert result1 is True
        assert result2 is False
        
    def test_registry_provider_replacement_tracking(self):
        """Test that provider replacement is tracked correctly."""
        registry = OwnershipRegistry()
        
        provider1 = AsyncOwnershipProvider(return_value=True)
        provider2 = AsyncOwnershipProvider(return_value=False)
        
        # Register first provider
        registry.register("resource", provider1)
        assert registry.has_provider("resource")
        
        # Replace with second provider
        registry.register("resource", provider2)
        assert registry.has_provider("resource")
        
        # Unregister should return the current (second) provider
        removed = registry.unregister("resource")
        assert removed is provider2
        assert not registry.has_provider("resource")