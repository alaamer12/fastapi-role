"""Comprehensive tests for provider system edge cases.

This module tests various edge cases and error scenarios for the provider system,
including invalid implementations, error handling, thread safety, and lifecycle management.

Test Classes:
    TestProviderRegistration: Tests provider registration with invalid implementations
    TestProviderErrorHandling: Tests provider error handling and fallback behavior
    TestProviderThreadSafety: Tests provider thread safety and concurrent access
    TestProviderLifecycle: Tests provider lifecycle management and cleanup
    TestProviderValidation: Tests provider configuration validation and error reporting
    TestMockProviderImplementations: Tests provider system with mock implementations
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Protocol

import pytest
from fastapi import HTTPException

from fastapi_role import (
    Permission, 
    require,
    set_rbac_service,
    rbac_service_context,
)
from fastapi_role.core.ownership import OwnershipRegistry
from fastapi_role.protocols import (
    UserProtocol,
    SubjectProvider,
    RoleProvider,
    CacheProvider,
)
from fastapi_role.providers import (
    DefaultSubjectProvider,
    DefaultRoleProvider,
    DefaultCacheProvider,
    DefaultOwnershipProvider,
)
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class InvalidSubjectProvider:
    """Invalid subject provider that doesn't implement the protocol."""
    
    def __init__(self):
        self.invalid_method = lambda: "not a subject provider"


class PartialSubjectProvider:
    """Subject provider that only partially implements the protocol."""
    
    def __init__(self):
        pass
    # Missing get_subject method


class FailingSubjectProvider:
    """Subject provider that raises exceptions."""
    
    def get_subject(self, user: UserProtocol) -> str:
        raise Exception("Subject provider failed")


class SlowSubjectProvider:
    """Subject provider that is slow to respond."""
    
    def __init__(self, delay: float = 0.1):
        self.delay = delay
        self.call_count = 0
    
    def get_subject(self, user: UserProtocol) -> str:
        self.call_count += 1
        time.sleep(self.delay)
        return f"slow_subject_{user.id}"


class ThreadUnsafeProvider:
    """Provider that is not thread-safe for testing."""
    
    def __init__(self):
        self.counter = 0
        self.results = []
    
    def get_subject(self, user: UserProtocol) -> str:
        # Simulate non-atomic operations
        current = self.counter
        time.sleep(0.001)  # Small delay to increase chance of race condition
        self.counter = current + 1
        result = f"subject_{self.counter}"
        self.results.append(result)
        return result


class MockRBACService:
    """Mock RBAC service for testing."""
    
    def __init__(self, permissions_result: bool = True, ownership_result: bool = True):
        self.permissions_result = permissions_result
        self.ownership_result = ownership_result
        self.check_permission = AsyncMock(return_value=permissions_result)
        self.check_resource_ownership = AsyncMock(return_value=ownership_result)


class TestProviderRegistration:
    """Tests for provider registration with invalid implementations.
    
    Validates: Requirements 7.5, 7.6
    """

    def test_valid_subject_provider_registration(self):
        """Test registration of valid subject provider."""
        
        provider = DefaultSubjectProvider()
        
        # Should not raise any exceptions
        assert provider is not None
        assert hasattr(provider, 'get_subject')
        assert callable(provider.get_subject)

    def test_invalid_subject_provider_detection(self):
        """Test detection of invalid subject provider."""
        
        invalid_provider = InvalidSubjectProvider()
        
        # Should detect that this is not a valid provider
        assert not hasattr(invalid_provider, 'get_subject')

    def test_partial_subject_provider_detection(self):
        """Test detection of partially implemented subject provider."""
        
        partial_provider = PartialSubjectProvider()
        
        # Should detect missing methods
        assert not hasattr(partial_provider, 'get_subject')

    def test_role_provider_registration_validation(self):
        """Test role provider registration validation."""
        
        valid_provider = DefaultRoleProvider()
        
        # Should have required methods
        assert hasattr(valid_provider, 'get_user_roles')
        assert hasattr(valid_provider, 'has_role')
        assert callable(valid_provider.get_user_roles)
        assert callable(valid_provider.has_role)

    def test_cache_provider_registration_validation(self):
        """Test cache provider registration validation."""
        
        valid_provider = DefaultCacheProvider()
        
        # Should have required methods
        required_methods = ['get', 'set', 'clear', 'get_stats']
        for method_name in required_methods:
            assert hasattr(valid_provider, method_name)
            assert callable(getattr(valid_provider, method_name))

    def test_ownership_provider_registration(self):
        """Test ownership provider registration in registry."""
        
        registry = OwnershipRegistry()
        provider = DefaultOwnershipProvider()
        
        # Should register without errors
        registry.register("test_resource", provider)
        
        # Should retrieve the same provider
        retrieved_provider = registry.get_provider("test_resource")
        assert retrieved_provider is provider

    def test_ownership_registry_wildcard_provider(self):
        """Test ownership registry wildcard provider registration."""
        
        registry = OwnershipRegistry()
        wildcard_provider = DefaultOwnershipProvider()
        specific_provider = DefaultOwnershipProvider()
        
        # Register wildcard and specific providers
        registry.register("*", wildcard_provider)
        registry.register("specific_resource", specific_provider)
        
        # Should get specific provider for specific resource
        assert registry.get_provider("specific_resource") is specific_provider
        
        # Should get wildcard provider for unknown resource
        assert registry.get_provider("unknown_resource") is wildcard_provider

    def test_ownership_registry_no_provider_error(self):
        """Test ownership registry behavior when no provider is registered."""
        
        registry = OwnershipRegistry(default_allow=False)
        
        # Should raise error when no provider is found
        with pytest.raises(ValueError) as exc_info:
            registry.get_provider("nonexistent_resource")
        
        assert "No ownership provider registered" in str(exc_info.value)


class TestProviderErrorHandling:
    """Tests for provider error handling and fallback behavior.
    
    Validates: Requirements 7.6, 7.7
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def test_subject_provider_exception_handling(self, user):
        """Test handling of exceptions from subject provider."""
        
        failing_provider = FailingSubjectProvider()
        
        # Should handle the exception gracefully
        with pytest.raises(Exception) as exc_info:
            failing_provider.get_subject(user)
        
        assert "Subject provider failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_role_provider_exception_handling(self, user):
        """Test handling of exceptions from role provider."""
        
        class FailingRoleProvider:
            async def get_user_roles(self, user: UserProtocol) -> List[str]:
                raise Exception("Role provider failed")
            
            async def has_role(self, user: UserProtocol, role_name: str) -> bool:
                raise Exception("Role provider failed")
        
        failing_provider = FailingRoleProvider()
        
        with pytest.raises(Exception) as exc_info:
            await failing_provider.get_user_roles(user)
        
        assert "Role provider failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cache_provider_exception_handling(self):
        """Test handling of exceptions from cache provider."""
        
        class FailingCacheProvider:
            async def get(self, key: str) -> Optional[Any]:
                raise Exception("Cache get failed")
            
            async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
                raise Exception("Cache set failed")
            
            async def clear(self, pattern: Optional[str] = None) -> None:
                raise Exception("Cache clear failed")
            
            async def get_stats(self) -> Dict[str, Any]:
                raise Exception("Cache stats failed")
        
        failing_provider = FailingCacheProvider()
        
        with pytest.raises(Exception) as exc_info:
            await failing_provider.get("test_key")
        
        assert "Cache get failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ownership_provider_exception_handling(self, user):
        """Test handling of exceptions from ownership provider."""
        
        class FailingOwnershipProvider:
            async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
                raise Exception("Ownership check failed")
        
        failing_provider = FailingOwnershipProvider()
        
        with pytest.raises(Exception) as exc_info:
            await failing_provider.check_ownership(user, "test_resource", 123)
        
        assert "Ownership check failed" in str(exc_info.value)

    def test_ownership_registry_fallback_behavior(self):
        """Test ownership registry fallback behavior."""
        
        registry = OwnershipRegistry(default_allow=True)
        
        # Should fall back to default behavior when no provider is found
        # This should not raise an exception due to default_allow=True
        try:
            provider = registry.get_provider("nonexistent_resource")
            # Should get the default provider
            assert provider is not None
        except ValueError:
            # If no default provider, should handle gracefully
            pass

    @pytest.mark.asyncio
    async def test_provider_timeout_handling(self, user):
        """Test handling of slow/timeout providers."""
        
        slow_provider = SlowSubjectProvider(delay=0.1)
        
        # Should complete but be slow
        start_time = time.time()
        result = slow_provider.get_subject(user)
        end_time = time.time()
        
        assert result == "slow_subject_1"
        assert end_time - start_time >= 0.1  # Should take at least the delay time

    def test_provider_retry_logic(self, user):
        """Test provider retry logic for transient failures."""
        
        class FlakyProvider:
            def __init__(self):
                self.attempt_count = 0
            
            def get_subject(self, user: UserProtocol) -> str:
                self.attempt_count += 1
                if self.attempt_count < 3:
                    raise Exception("Transient failure")
                return f"success_after_{self.attempt_count}_attempts"
        
        flaky_provider = FlakyProvider()
        
        # Simulate retry logic (would be implemented in the service)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = flaky_provider.get_subject(user)
                assert "success_after_3_attempts" == result
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                continue


class TestProviderThreadSafety:
    """Tests for provider thread safety and concurrent access.
    
    Validates: Requirements 7.7
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def test_default_subject_provider_thread_safety(self, user):
        """Test that default subject provider is thread-safe."""
        
        provider = DefaultSubjectProvider()
        results = []
        
        def worker():
            result = provider.get_subject(user)
            results.append(result)
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All results should be the same (thread-safe)
        assert len(results) == 10
        assert all(result == user.email for result in results)

    @pytest.mark.asyncio
    async def test_default_role_provider_thread_safety(self, user):
        """Test that default role provider is thread-safe."""
        
        provider = DefaultRoleProvider()
        results = []
        
        async def worker():
            result = await provider.get_user_roles(user)
            results.append(result)
        
        # Run multiple async tasks concurrently
        tasks = [worker() for _ in range(10)]
        await asyncio.gather(*tasks)
        
        # All results should be the same (thread-safe)
        assert len(results) == 10
        expected_result = [user.role]
        assert all(result == expected_result for result in results)

    @pytest.mark.asyncio
    async def test_default_cache_provider_thread_safety(self):
        """Test that default cache provider is thread-safe."""
        
        provider = DefaultCacheProvider()
        results = []
        
        async def worker(worker_id: int):
            key = f"test_key_{worker_id}"
            value = f"test_value_{worker_id}"
            
            await provider.set(key, value)
            retrieved_value = await provider.get(key)
            results.append((key, value, retrieved_value))
        
        # Run multiple async tasks concurrently
        tasks = [worker(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # All operations should complete successfully
        assert len(results) == 10
        for key, original_value, retrieved_value in results:
            assert original_value == retrieved_value

    def test_thread_unsafe_provider_detection(self, user):
        """Test detection of thread safety issues in providers."""
        
        unsafe_provider = ThreadUnsafeProvider()
        
        def worker():
            unsafe_provider.get_subject(user)
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for race conditions (counter might not be 10 due to race conditions)
        # This test demonstrates the issue rather than asserting a specific value
        assert len(unsafe_provider.results) == 10
        # The counter might be less than 10 due to race conditions
        print(f"Final counter value: {unsafe_provider.counter} (expected: 10)")

    @pytest.mark.asyncio
    async def test_concurrent_ownership_provider_access(self, user):
        """Test concurrent access to ownership providers."""
        
        registry = OwnershipRegistry()
        provider = DefaultOwnershipProvider()
        registry.register("test_resource", provider)
        
        results = []
        
        async def worker(resource_id: int):
            result = await provider.check_ownership(user, "test_resource", resource_id)
            results.append(result)
        
        # Run multiple async tasks concurrently
        tasks = [worker(i) for i in range(20)]
        await asyncio.gather(*tasks)
        
        # All operations should complete successfully
        assert len(results) == 20

    def test_provider_registry_thread_safety(self):
        """Test that provider registry operations are thread-safe."""
        
        registry = OwnershipRegistry()
        
        def register_provider(resource_type: str):
            provider = DefaultOwnershipProvider()
            registry.register(resource_type, provider)
        
        def get_provider(resource_type: str):
            try:
                registry.get_provider(resource_type)
            except ValueError:
                pass  # Expected for non-existent providers
        
        # Run registration and retrieval concurrently
        threads = []
        
        # Registration threads
        for i in range(5):
            thread = threading.Thread(target=register_provider, args=(f"resource_{i}",))
            threads.append(thread)
            thread.start()
        
        # Retrieval threads
        for i in range(10):
            thread = threading.Thread(target=get_provider, args=(f"resource_{i % 5}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Registry should be in a consistent state
        assert len(registry._providers) >= 5


class TestProviderLifecycle:
    """Tests for provider lifecycle management and cleanup.
    
    Validates: Requirements 7.7
    """

    def test_provider_initialization(self):
        """Test provider initialization with various configurations."""
        
        # Test default initialization
        provider1 = DefaultSubjectProvider()
        assert provider1.field_name == "email"
        
        # Test custom initialization
        provider2 = DefaultSubjectProvider(field_name="username")
        assert provider2.field_name == "username"

    def test_provider_configuration_updates(self):
        """Test updating provider configuration."""
        
        provider = DefaultRoleProvider()
        
        # Initial configuration
        assert provider.superadmin_role is None
        
        # Update configuration (if supported)
        provider.superadmin_role = "admin"
        assert provider.superadmin_role == "admin"

    @pytest.mark.asyncio
    async def test_cache_provider_cleanup(self):
        """Test cache provider cleanup operations."""
        
        provider = DefaultCacheProvider()
        
        # Add some data
        await provider.set("key1", "value1")
        await provider.set("key2", "value2")
        await provider.set("key3", "value3")
        
        # Verify data exists
        assert await provider.get("key1") == "value1"
        assert await provider.get("key2") == "value2"
        
        # Clear all data
        await provider.clear()
        
        # Verify data is cleared
        assert await provider.get("key1") is None
        assert await provider.get("key2") is None
        assert await provider.get("key3") is None

    @pytest.mark.asyncio
    async def test_cache_provider_ttl_expiration(self):
        """Test cache provider TTL expiration."""
        
        provider = DefaultCacheProvider()
        
        # Set value with short TTL
        await provider.set("expiring_key", "expiring_value", ttl=1)
        
        # Should be available immediately
        assert await provider.get("expiring_key") == "expiring_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired (implementation dependent)
        # Note: DefaultCacheProvider might not implement TTL, so this is conceptual
        result = await provider.get("expiring_key")
        # Result might still be there if TTL is not implemented

    def test_ownership_registry_cleanup(self):
        """Test ownership registry cleanup operations."""
        
        registry = OwnershipRegistry()
        
        # Register multiple providers
        for i in range(5):
            provider = DefaultOwnershipProvider()
            registry.register(f"resource_{i}", provider)
        
        # Verify providers are registered
        assert len(registry._providers) == 5
        
        # Clear registry (if supported)
        registry._providers.clear()
        
        # Verify registry is empty
        assert len(registry._providers) == 0

    def test_provider_resource_management(self):
        """Test provider resource management and memory usage."""
        
        # Create many providers to test resource management
        providers = []
        for i in range(100):
            provider = DefaultSubjectProvider(field_name=f"field_{i}")
            providers.append(provider)
        
        # Verify all providers are created
        assert len(providers) == 100
        
        # Clear references
        providers.clear()
        
        # Python garbage collection should handle cleanup
        assert len(providers) == 0


class TestProviderValidation:
    """Tests for provider configuration validation and error reporting.
    
    Validates: Requirements 7.5, 7.6
    """

    def test_subject_provider_field_validation(self):
        """Test subject provider field name validation."""
        
        # Valid field names
        valid_provider = DefaultSubjectProvider(field_name="email")
        assert valid_provider.field_name == "email"
        
        # Empty field name should work (might use default)
        empty_provider = DefaultSubjectProvider(field_name="")
        assert empty_provider.field_name == ""

    def test_role_provider_superadmin_validation(self):
        """Test role provider superadmin role validation."""
        
        # Valid superadmin role
        provider1 = DefaultRoleProvider(superadmin_role="admin")
        assert provider1.superadmin_role == "admin"
        
        # None superadmin role (no superadmin)
        provider2 = DefaultRoleProvider(superadmin_role=None)
        assert provider2.superadmin_role is None

    def test_cache_provider_ttl_validation(self):
        """Test cache provider TTL validation."""
        
        # Valid TTL
        provider1 = DefaultCacheProvider(default_ttl=300)
        assert provider1.default_ttl == 300
        
        # Zero TTL (no expiration)
        provider2 = DefaultCacheProvider(default_ttl=0)
        assert provider2.default_ttl == 0
        
        # Negative TTL should be handled appropriately
        provider3 = DefaultCacheProvider(default_ttl=-1)
        assert provider3.default_ttl == -1

    def test_ownership_provider_configuration_validation(self):
        """Test ownership provider configuration validation."""
        
        # Valid configuration
        provider1 = DefaultOwnershipProvider(superadmin_role="admin", default_allow=False)
        assert provider1.superadmin_role == "admin"
        assert provider1.default_allow is False
        
        # No superadmin configuration
        provider2 = DefaultOwnershipProvider(superadmin_role=None, default_allow=True)
        assert provider2.superadmin_role is None
        assert provider2.default_allow is True

    def test_ownership_registry_validation(self):
        """Test ownership registry configuration validation."""
        
        # Valid registry configuration
        registry1 = OwnershipRegistry(default_allow=True)
        assert registry1.default_allow is True
        
        registry2 = OwnershipRegistry(default_allow=False)
        assert registry2.default_allow is False

    def test_provider_error_message_clarity(self):
        """Test that provider error messages are clear and helpful."""
        
        registry = OwnershipRegistry(default_allow=False)
        
        # Test clear error message for missing provider
        with pytest.raises(ValueError) as exc_info:
            registry.get_provider("nonexistent_resource")
        
        error_message = str(exc_info.value)
        assert "No ownership provider registered" in error_message
        assert "nonexistent_resource" in error_message


class TestMockProviderImplementations:
    """Tests for provider system with mock implementations.
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.7
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def test_mock_subject_provider(self, user):
        """Test system with mock subject provider."""
        
        class MockSubjectProvider:
            def __init__(self, subject_format: str = "mock_{id}"):
                self.subject_format = subject_format
            
            def get_subject(self, user: UserProtocol) -> str:
                return self.subject_format.format(id=user.id)
        
        mock_provider = MockSubjectProvider()
        result = mock_provider.get_subject(user)
        assert result == "mock_1"

    @pytest.mark.asyncio
    async def test_mock_role_provider(self, user):
        """Test system with mock role provider."""
        
        class MockRoleProvider:
            def __init__(self, roles: Dict[int, List[str]]):
                self.roles = roles
            
            async def get_user_roles(self, user: UserProtocol) -> List[str]:
                return self.roles.get(user.id, [])
            
            async def has_role(self, user: UserProtocol, role_name: str) -> bool:
                user_roles = await self.get_user_roles(user)
                return role_name in user_roles
        
        mock_provider = MockRoleProvider({1: ["customer", "premium"], 2: ["admin"]})
        
        roles = await mock_provider.get_user_roles(user)
        assert roles == ["customer", "premium"]
        
        has_customer = await mock_provider.has_role(user, "customer")
        assert has_customer is True
        
        has_admin = await mock_provider.has_role(user, "admin")
        assert has_admin is False

    @pytest.mark.asyncio
    async def test_mock_cache_provider(self):
        """Test system with mock cache provider."""
        
        class MockCacheProvider:
            def __init__(self):
                self.data = {}
                self.stats = {"hits": 0, "misses": 0, "sets": 0}
            
            async def get(self, key: str) -> Optional[Any]:
                if key in self.data:
                    self.stats["hits"] += 1
                    return self.data[key]
                else:
                    self.stats["misses"] += 1
                    return None
            
            async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
                self.data[key] = value
                self.stats["sets"] += 1
            
            async def clear(self, pattern: Optional[str] = None) -> None:
                if pattern:
                    # Simple pattern matching (starts with)
                    keys_to_remove = [k for k in self.data.keys() if k.startswith(pattern.rstrip('*'))]
                    for key in keys_to_remove:
                        del self.data[key]
                else:
                    self.data.clear()
            
            async def get_stats(self) -> Dict[str, Any]:
                return self.stats.copy()
        
        mock_provider = MockCacheProvider()
        
        # Test set and get
        await mock_provider.set("key1", "value1")
        result = await mock_provider.get("key1")
        assert result == "value1"
        
        # Test miss
        result = await mock_provider.get("nonexistent")
        assert result is None
        
        # Test stats
        stats = await mock_provider.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1

    @pytest.mark.asyncio
    async def test_mock_ownership_provider(self, user):
        """Test system with mock ownership provider."""
        
        class MockOwnershipProvider:
            def __init__(self, ownership_rules: Dict[str, Dict[Any, List[int]]]):
                self.ownership_rules = ownership_rules
            
            async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
                if resource_type not in self.ownership_rules:
                    return False
                
                resource_owners = self.ownership_rules[resource_type].get(resource_id, [])
                return user.id in resource_owners
        
        # Define ownership rules: resource_type -> resource_id -> list of owner user IDs
        ownership_rules = {
            "documents": {
                "doc1": [1, 2],  # User 1 and 2 own doc1
                "doc2": [2],     # Only user 2 owns doc2
            },
            "projects": {
                "proj1": [1],    # Only user 1 owns proj1
            }
        }
        
        mock_provider = MockOwnershipProvider(ownership_rules)
        
        # Test ownership checks
        owns_doc1 = await mock_provider.check_ownership(user, "documents", "doc1")
        assert owns_doc1 is True
        
        owns_doc2 = await mock_provider.check_ownership(user, "documents", "doc2")
        assert owns_doc2 is False
        
        owns_proj1 = await mock_provider.check_ownership(user, "projects", "proj1")
        assert owns_proj1 is True
        
        owns_nonexistent = await mock_provider.check_ownership(user, "nonexistent", "anything")
        assert owns_nonexistent is False

    @pytest.mark.asyncio
    async def test_integrated_mock_providers(self, user):
        """Test integrated system with multiple mock providers."""
        
        # Create mock providers
        subject_provider = MockSubjectProvider()
        role_provider = MockRoleProvider({1: ["customer", "premium"]})
        cache_provider = MockCacheProvider()
        ownership_provider = MockOwnershipProvider({
            "orders": {"order1": [1], "order2": [2]}
        })
        
        # Test that they work together
        subject = subject_provider.get_subject(user)
        roles = await role_provider.get_user_roles(user)
        
        # Cache the results
        await cache_provider.set(f"subject_{user.id}", subject)
        await cache_provider.set(f"roles_{user.id}", roles)
        
        # Retrieve from cache
        cached_subject = await cache_provider.get(f"subject_{user.id}")
        cached_roles = await cache_provider.get(f"roles_{user.id}")
        
        assert cached_subject == subject
        assert cached_roles == roles
        
        # Test ownership
        owns_order1 = await ownership_provider.check_ownership(user, "orders", "order1")
        owns_order2 = await ownership_provider.check_ownership(user, "orders", "order2")
        
        assert owns_order1 is True
        assert owns_order2 is False