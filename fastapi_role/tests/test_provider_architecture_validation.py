"""Comprehensive validation tests for the provider architecture.

This module validates that all provider protocols work correctly with custom
implementations, default providers handle edge cases, and provider registration
and validation works as expected.

Test Classes:
    TestProviderProtocolCompliance: Tests for protocol compliance validation
    TestDefaultProviderEdgeCases: Tests for edge cases in default providers
    TestProviderRegistration: Tests for provider registration and validation
    TestMockProviderImplementations: Tests with mock provider implementations
    TestOwnershipProviderSystem: Tests for ownership provider system
    TestDatabaseProviderSystem: Tests for database provider system
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Any, Optional, List

from fastapi_role.protocols.providers import SubjectProvider, RoleProvider, CacheProvider
from fastapi_role.protocols.database import DatabaseProvider
from fastapi_role.providers import (
    DefaultSubjectProvider, DefaultRoleProvider, DefaultCacheProvider,
    DefaultOwnershipProvider, InMemoryDatabaseProvider, SQLAlchemyDatabaseProvider
)
from fastapi_role.core.ownership import OwnershipProvider, OwnershipRegistry
from tests.conftest import TestUser as User


class MockUser:
    """Mock user for testing edge cases."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestProviderProtocolCompliance:
    """Tests for provider protocol compliance validation.
    
    Validates: Requirements 7.1, 7.2, 7.5
    """

    def test_subject_provider_protocol_compliance(self):
        """Test that custom subject providers can implement the protocol."""
        
        class CustomSubjectProvider:
            def get_subject(self, user) -> str:
                return f"custom_{user.id}"
        
        provider = CustomSubjectProvider()
        user = User(id=123, email="test@example.com", role="user")
        
        # Should work with protocol
        subject = provider.get_subject(user)
        assert subject == "custom_123"

    def test_role_provider_protocol_compliance(self):
        """Test that custom role providers can implement the protocol."""
        
        class CustomRoleProvider:
            def get_role(self, user) -> str:
                return f"custom_{user.role}"
            
            def has_role(self, user, role_name: str) -> bool:
                return user.role == role_name or role_name == "universal"
        
        provider = CustomRoleProvider()
        user = User(id=1, role="admin")
        
        # Test protocol methods
        assert provider.get_role(user) == "custom_admin"
        assert provider.has_role(user, "admin") is True
        assert provider.has_role(user, "universal") is True
        assert provider.has_role(user, "other") is False

    def test_cache_provider_protocol_compliance(self):
        """Test that custom cache providers can implement the protocol."""
        
        class CustomCacheProvider:
            def __init__(self):
                self._data = {}
            
            def get(self, key: str) -> Optional[bool]:
                return self._data.get(key)
            
            def set(self, key: str, value: bool, ttl: Optional[int] = None) -> None:
                self._data[key] = value
            
            def clear(self) -> None:
                self._data.clear()
            
            def get_stats(self) -> dict:
                return {"size": len(self._data), "custom": True}
        
        provider = CustomCacheProvider()
        
        # Test protocol methods
        assert provider.get("missing") is None
        provider.set("key1", True)
        assert provider.get("key1") is True
        
        stats = provider.get_stats()
        assert stats["size"] == 1
        assert stats["custom"] is True
        
        provider.clear()
        assert provider.get("key1") is None

    def test_ownership_provider_protocol_compliance(self):
        """Test that custom ownership providers can implement the protocol."""
        
        class CustomOwnershipProvider:
            async def check_ownership(self, user, resource_type: str, resource_id: Any) -> bool:
                # Custom logic: users own resources with their ID
                return str(resource_id) == str(user.id)
        
        provider = CustomOwnershipProvider()
        user = User(id=123, role="user")
        
        # Test protocol method
        import asyncio
        
        # User owns resource with their ID
        result = asyncio.run(provider.check_ownership(user, "document", 123))
        assert result is True
        
        # User doesn't own resource with different ID
        result = asyncio.run(provider.check_ownership(user, "document", 456))
        assert result is False


class TestDefaultProviderEdgeCases:
    """Tests for edge cases in default providers.
    
    Validates: Requirements 7.2, 7.6
    """

    def test_default_subject_provider_missing_field(self):
        """Test subject provider with missing field."""
        provider = DefaultSubjectProvider(field_name="nonexistent")
        user = User(id=1, email="test@example.com", role="user")
        
        with pytest.raises(AttributeError):
            provider.get_subject(user)

    def test_default_subject_provider_none_field(self):
        """Test subject provider with None field value."""
        provider = DefaultSubjectProvider(field_name="email")
        user = MockUser(id=1, email=None, role="user")
        
        subject = provider.get_subject(user)
        assert subject == "None"

    def test_default_role_provider_missing_role(self):
        """Test role provider with missing role attribute."""
        provider = DefaultRoleProvider()
        user = MockUser(id=1, email="test@example.com")  # No role attribute
        
        with pytest.raises(AttributeError):
            provider.get_role(user)

    def test_default_role_provider_none_role(self):
        """Test role provider with None role value."""
        provider = DefaultRoleProvider()
        user = MockUser(id=1, role=None)
        
        role = provider.get_role(user)
        assert role is None

    def test_default_cache_provider_concurrent_access(self):
        """Test cache provider under concurrent access simulation."""
        import threading
        import time
        
        provider = DefaultCacheProvider()
        results = []
        
        def worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                provider.set(key, True)
                result = provider.get(key)
                results.append(result)
                time.sleep(0.001)  # Small delay to simulate real work
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert len(results) == 50
        assert all(result is True for result in results)

    def test_default_ownership_provider_edge_cases(self):
        """Test ownership provider with various edge cases."""
        import asyncio
        
        # Test with no superadmin role
        provider = DefaultOwnershipProvider(default_allow=True)
        user = User(id=1, role="user")
        
        result = asyncio.run(provider.check_ownership(user, "document", 123))
        assert result is True  # default_allow=True
        
        # Test with superadmin role but user doesn't have it
        provider = DefaultOwnershipProvider(superadmin_role="admin", default_allow=False)
        user = User(id=1, role="user")
        
        result = asyncio.run(provider.check_ownership(user, "document", 123))
        assert result is False  # Not superadmin, default_allow=False
        
        # Test with allowed roles
        provider = DefaultOwnershipProvider(
            allowed_roles={"manager", "editor"}, 
            default_allow=False
        )
        
        manager_user = User(id=1, role="manager")
        regular_user = User(id=2, role="user")
        
        result = asyncio.run(provider.check_ownership(manager_user, "document", 123))
        assert result is True  # Manager is in allowed_roles
        
        result = asyncio.run(provider.check_ownership(regular_user, "document", 123))
        assert result is False  # User not in allowed_roles


class TestProviderRegistration:
    """Tests for provider registration and validation.
    
    Validates: Requirements 7.5, 7.6
    """

    def test_ownership_registry_registration(self):
        """Test ownership provider registration."""
        registry = OwnershipRegistry(default_allow=False)
        
        class TestOwnershipProvider:
            async def check_ownership(self, user, resource_type: str, resource_id: Any) -> bool:
                return resource_type == "allowed_resource"
        
        provider = TestOwnershipProvider()
        
        # Register provider
        registry.register("document", provider)
        
        # Verify registration
        assert registry.has_provider("document") is True
        assert registry.has_provider("other") is False

    def test_ownership_registry_check_with_provider(self):
        """Test ownership checking with registered provider."""
        import asyncio
        
        registry = OwnershipRegistry(default_allow=False)
        
        class TestOwnershipProvider:
            async def check_ownership(self, user, resource_type: str, resource_id: Any) -> bool:
                return resource_id == 123  # Only allow resource 123
        
        provider = TestOwnershipProvider()
        registry.register("document", provider)
        
        user = User(id=1, role="user")
        
        # Should use registered provider
        result = asyncio.run(registry.check(user, "document", 123))
        assert result is True
        
        result = asyncio.run(registry.check(user, "document", 456))
        assert result is False

    def test_ownership_registry_check_without_provider(self):
        """Test ownership checking without registered provider."""
        import asyncio
        
        registry = OwnershipRegistry(default_allow=True)
        user = User(id=1, role="user")
        
        # Should use default behavior
        result = asyncio.run(registry.check(user, "unregistered", 123))
        assert result is True  # default_allow=True

    def test_ownership_registry_unregister(self):
        """Test unregistering ownership providers."""
        registry = OwnershipRegistry()
        
        class TestOwnershipProvider:
            async def check_ownership(self, user, resource_type: str, resource_id: Any) -> bool:
                return True
        
        provider = TestOwnershipProvider()
        registry.register("document", provider)
        
        # Verify registered
        assert registry.has_provider("document") is True
        
        # Unregister
        removed_provider = registry.unregister("document")
        assert removed_provider is provider
        assert registry.has_provider("document") is False
        
        # Unregister non-existent
        removed_provider = registry.unregister("nonexistent")
        assert removed_provider is None


class TestMockProviderImplementations:
    """Tests with mock provider implementations.
    
    Validates: Requirements 7.1, 7.3, 7.4
    """

    def test_mock_subject_provider(self):
        """Test with mock subject provider."""
        mock_provider = Mock(spec=SubjectProvider)
        mock_provider.get_subject.return_value = "mocked_subject"
        
        user = User(id=1, email="test@example.com", role="user")
        
        subject = mock_provider.get_subject(user)
        assert subject == "mocked_subject"
        mock_provider.get_subject.assert_called_once_with(user)

    def test_mock_role_provider(self):
        """Test with mock role provider."""
        mock_provider = Mock(spec=RoleProvider)
        mock_provider.get_role.return_value = "mocked_role"
        mock_provider.has_role.return_value = True
        
        user = User(id=1, role="user")
        
        role = mock_provider.get_role(user)
        assert role == "mocked_role"
        
        has_role = mock_provider.has_role(user, "admin")
        assert has_role is True
        
        mock_provider.get_role.assert_called_once_with(user)
        mock_provider.has_role.assert_called_once_with(user, "admin")

    def test_mock_cache_provider(self):
        """Test with mock cache provider."""
        mock_provider = Mock(spec=CacheProvider)
        mock_provider.get.return_value = True
        mock_provider.get_stats.return_value = {"mocked": True}
        
        result = mock_provider.get("test_key")
        assert result is True
        
        mock_provider.set("test_key", False, ttl=300)
        mock_provider.clear()
        
        stats = mock_provider.get_stats()
        assert stats["mocked"] is True
        
        # Verify all methods were called
        mock_provider.get.assert_called_once_with("test_key")
        mock_provider.set.assert_called_once_with("test_key", False, ttl=300)
        mock_provider.clear.assert_called_once()
        mock_provider.get_stats.assert_called_once()

    def test_mock_ownership_provider_async(self):
        """Test with mock async ownership provider."""
        import asyncio
        
        mock_provider = Mock()
        mock_provider.check_ownership = AsyncMock(return_value=True)
        
        user = User(id=1, role="user")
        
        result = asyncio.run(mock_provider.check_ownership(user, "document", 123))
        assert result is True
        
        mock_provider.check_ownership.assert_called_once_with(user, "document", 123)


class TestDatabaseProviderSystem:
    """Tests for database provider system.
    
    Validates: Requirements 7.4, 7.6
    """

    def test_in_memory_database_provider_basic_operations(self):
        """Test basic operations of in-memory database provider."""
        import asyncio
        
        provider = InMemoryDatabaseProvider()
        user = User(id=1, email="test@example.com", role="user")
        
        # Test user role persistence
        result = asyncio.run(provider.persist_user_role(user, "admin"))
        assert result is True
        
        roles = asyncio.run(provider.load_user_roles(user))
        assert "admin" in roles
        
        # Test policy persistence
        policy = ["user", "document", "read"]
        result = asyncio.run(provider.persist_policy(policy))
        assert result is True
        
        policies = asyncio.run(provider.load_policies())
        assert policy in policies
        
        # Test policy removal
        result = asyncio.run(provider.remove_policy(policy))
        assert result is True
        
        policies = asyncio.run(provider.load_policies())
        assert policy not in policies

    def test_in_memory_database_provider_transactions(self):
        """Test transaction support in in-memory database provider."""
        import asyncio
        
        provider = InMemoryDatabaseProvider()
        
        # Test transaction lifecycle
        txn = asyncio.run(provider.transaction_begin())
        assert txn is not None
        
        result = asyncio.run(provider.transaction_commit(txn))
        assert result is True
        
        # Test rollback
        txn = asyncio.run(provider.transaction_begin())
        result = asyncio.run(provider.transaction_rollback(txn))
        assert result is True

    def test_in_memory_database_provider_sync_operations(self):
        """Test synchronous operations of in-memory database provider."""
        provider = InMemoryDatabaseProvider()
        user = User(id=1, email="test@example.com", role="user")
        
        # Test sync user role persistence
        result = provider.persist_user_role_sync(user, "admin")
        assert result is True
        
        roles = provider.load_user_roles_sync(user)
        assert "admin" in roles
        
        # Test sync policy operations
        policy = ["user", "document", "read"]
        result = provider.persist_policy_sync(policy)
        assert result is True
        
        policies = provider.load_policies_sync()
        assert policy in policies
        
        result = provider.remove_policy_sync(policy)
        assert result is True

    def test_sqlalchemy_database_provider_initialization(self):
        """Test SQLAlchemy database provider initialization."""
        mock_session_factory = Mock()
        mock_session = Mock()
        mock_session_factory.return_value = mock_session
        
        provider = SQLAlchemyDatabaseProvider(
            session_factory=mock_session_factory,
            user_table="users",
            policy_table="policies"
        )
        
        assert provider.session_factory is mock_session_factory
        assert provider.user_table == "users"
        assert provider.policy_table == "policies"

    def test_sqlalchemy_database_provider_error_handling(self):
        """Test SQLAlchemy database provider error handling."""
        import asyncio
        
        # Mock session factory that raises exception
        def failing_session_factory():
            raise Exception("Database connection failed")
        
        provider = SQLAlchemyDatabaseProvider(session_factory=failing_session_factory)
        user = User(id=1, email="test@example.com", role="user")
        
        # Should handle errors gracefully
        result = asyncio.run(provider.persist_user_role(user, "admin"))
        assert result is False
        
        result = asyncio.run(provider.persist_policy(["user", "doc", "read"]))
        assert result is False
        
        policies = asyncio.run(provider.load_policies())
        assert policies == []
        
        roles = asyncio.run(provider.load_user_roles(user))
        assert roles == []


class TestProviderSystemIntegration:
    """Tests for provider system integration scenarios.
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
    """

    def test_multiple_provider_types_together(self):
        """Test using multiple provider types together."""
        import asyncio
        
        # Create providers
        subject_provider = DefaultSubjectProvider(field_name="email")
        role_provider = DefaultRoleProvider(superadmin_role="admin")
        cache_provider = DefaultCacheProvider(default_ttl=300)
        ownership_provider = DefaultOwnershipProvider(superadmin_role="admin")
        
        user = User(id=1, email="test@example.com", role="admin")
        
        # Test subject extraction
        subject = subject_provider.get_subject(user)
        assert subject == "test@example.com"
        
        # Test role checking
        role = role_provider.get_role(user)
        assert role == "admin"
        assert role_provider.has_role(user, "any_role") is True  # superadmin bypass
        
        # Test caching
        cache_provider.set("test_key", True)
        assert cache_provider.get("test_key") is True
        
        # Test ownership
        result = asyncio.run(ownership_provider.check_ownership(user, "document", 123))
        assert result is True  # superadmin bypass

    def test_provider_configuration_flexibility(self):
        """Test provider configuration flexibility."""
        # Test different configurations
        configs = [
            {"superadmin_role": "root", "default_allow": True},
            {"superadmin_role": None, "default_allow": False},
            {"allowed_roles": {"manager", "editor"}, "default_allow": False},
        ]
        
        for config in configs:
            provider = DefaultOwnershipProvider(**config)
            assert provider.superadmin_role == config.get("superadmin_role")
            assert provider.default_allow == config.get("default_allow", False)
            assert provider.allowed_roles == config.get("allowed_roles", set())

    def test_provider_thread_safety_simulation(self):
        """Test provider thread safety under concurrent access."""
        import threading
        import time
        
        cache_provider = DefaultCacheProvider()
        ownership_registry = OwnershipRegistry()
        
        results = []
        
        def worker(worker_id):
            # Cache operations
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                cache_provider.set(key, True)
                result = cache_provider.get(key)
                results.append(("cache", worker_id, i, result))
            
            # Registry operations
            class WorkerOwnershipProvider:
                async def check_ownership(self, user, resource_type: str, resource_id: Any) -> bool:
                    return True
            
            provider = WorkerOwnershipProvider()
            resource_type = f"resource_{worker_id}"
            ownership_registry.register(resource_type, provider)
            has_provider = ownership_registry.has_provider(resource_type)
            results.append(("registry", worker_id, has_provider))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        cache_results = [r for r in results if r[0] == "cache"]
        registry_results = [r for r in results if r[0] == "registry"]
        
        assert len(cache_results) == 50  # 5 workers * 10 operations
        assert all(r[3] is True for r in cache_results)  # All cache operations succeeded
        
        assert len(registry_results) == 5  # 5 workers
        assert all(r[2] is True for r in registry_results)  # All registrations succeeded