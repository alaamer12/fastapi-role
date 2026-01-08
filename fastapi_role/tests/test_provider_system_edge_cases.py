"""Comprehensive tests for provider system edge cases.

This module provides thorough testing of the provider system including
registration, error handling, thread safety, and lifecycle management.

Test Classes:
    TestProviderRegistration: Tests provider registration with various implementations
    TestProviderErrorHandling: Tests error handling and fallback behavior
    TestProviderThreadSafety: Tests thread safety and concurrent access
    TestProviderLifecycle: Tests lifecycle management and cleanup
    TestProviderConfiguration: Tests configuration validation and error reporting
    TestProviderMockImplementations: Tests with mock implementations and edge cases
"""

import asyncio
import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Protocol

import pytest
from fastapi import HTTPException

from fastapi_role import (
    Permission, 
    Privilege, 
    ResourceOwnership, 
    require,
    set_rbac_service,
    rbac_service_context,
)
from fastapi_role.core.roles import create_roles


class TestProviderRegistration:
    """Tests for provider registration with various implementations.
    
    Validates: Requirements 9.4
    """

    def teardown_method(self):
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    def test_valid_provider_registration(self):
        """Test registration of valid provider implementations."""
        
        class ValidRBACService:
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        service = ValidRBACService()
        
        # Should register without errors
        set_rbac_service(service)
        
        # Verify registration
        from fastapi_role.rbac import _service_registry
        assert len(_service_registry) > 0

    def test_invalid_provider_registration(self):
        """Test registration of invalid provider implementations."""
        
        class InvalidRBACService:
            # Missing required methods
            def some_other_method(self):
                pass
        
        invalid_service = InvalidRBACService()
        
        # Should handle gracefully (may not raise during registration but during use)
        set_rbac_service(invalid_service)

    def test_partial_provider_implementation(self):
        """Test registration of partially implemented providers."""
        
        class PartialRBACService:
            async def check_permission(self, user, resource, action, context=None):
                return True
            # Missing check_resource_ownership method
        
        partial_service = PartialRBACService()
        set_rbac_service(partial_service)
        
        # Should register but may fail during ownership checks

    def test_multiple_provider_registration(self):
        """Test registration of multiple provider instances."""
        
        class RBACService1:
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        class RBACService2:
            async def check_permission(self, user, resource, action, context=None):
                return False
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return False
        
        service1 = RBACService1()
        service2 = RBACService2()
        
        # Register multiple services
        set_rbac_service(service1, "service1")
        set_rbac_service(service2, "service2")
        
        # Verify both are registered
        from fastapi_role.rbac import _service_registry
        assert len(_service_registry) >= 2

    def test_provider_replacement(self):
        """Test replacing an existing provider."""
        
        class OriginalService:
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        class ReplacementService:
            async def check_permission(self, user, resource, action, context=None):
                return False
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return False
        
        original = OriginalService()
        replacement = ReplacementService()
        
        # Register original
        set_rbac_service(original, "test_service")
        
        # Replace with new service
        set_rbac_service(replacement, "test_service")
        
        # Should have replaced the original

    def test_provider_with_custom_attributes(self):
        """Test registration of providers with custom attributes."""
        
        class CustomRBACService:
            def __init__(self):
                self.custom_config = {"timeout": 30, "retries": 3}
                self.metrics = {"calls": 0, "errors": 0}
            
            async def check_permission(self, user, resource, action, context=None):
                self.metrics["calls"] += 1
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                self.metrics["calls"] += 1
                return True
        
        custom_service = CustomRBACService()
        set_rbac_service(custom_service)
        
        # Should register successfully with custom attributes

    def test_provider_with_inheritance(self):
        """Test registration of providers using inheritance."""
        
        class BaseRBACService:
            async def check_permission(self, user, resource, action, context=None):
                return True
        
        class ExtendedRBACService(BaseRBACService):
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
            
            async def additional_method(self):
                return "extended_functionality"
        
        extended_service = ExtendedRBACService()
        set_rbac_service(extended_service)
        
        # Should register successfully


class TestProviderErrorHandling:
    """Tests for provider error handling and fallback behavior.
    
    Validates: Requirements 9.4
    """

    def teardown_method(self):
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.fixture
    def user(self):
        """Create a test user."""
        class TestUser:
            def __init__(self):
                self.id = 1
                self.email = "test@example.com"
                self.role = "user"
        return TestUser()

    @pytest.mark.asyncio
    async def test_permission_check_error_handling(self, user):
        """Test error handling when permission check fails."""
        
        class FailingPermissionService:
            async def check_permission(self, user, resource, action, context=None):
                raise Exception("Permission service unavailable")
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        failing_service = FailingPermissionService()
        
        @require(Permission("test", "action"))
        async def test_function(current_user, rbac_service):
            return "should_not_reach_here"
        
        # Should handle permission check error gracefully
        with pytest.raises(HTTPException) as exc_info:
            await test_function(user, failing_service)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_ownership_check_error_handling(self, user):
        """Test error handling when ownership check fails."""
        
        class FailingOwnershipService:
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                raise Exception("Ownership service unavailable")
        
        failing_service = FailingOwnershipService()
        
        @require(ResourceOwnership("resource"))
        async def test_function(resource_id: int, current_user, rbac_service):
            return "should_not_reach_here"
        
        # Should handle ownership check error gracefully
        with pytest.raises(HTTPException) as exc_info:
            await test_function(123, user, failing_service)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, user):
        """Test error handling when provider operations timeout."""
        
        class SlowService:
            async def check_permission(self, user, resource, action, context=None):
                await asyncio.sleep(10)  # Simulate slow operation
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        slow_service = SlowService()
        
        @require(Permission("slow", "test"))
        async def test_function(current_user, rbac_service):
            return "should_not_reach_here"
        
        # Should handle timeout gracefully (if timeout is implemented)
        start_time = time.time()
        try:
            await asyncio.wait_for(test_function(user, slow_service), timeout=1.0)
        except (asyncio.TimeoutError, HTTPException):
            # Either timeout or HTTP exception is acceptable
            pass
        end_time = time.time()
        
        # Should not take longer than timeout + small buffer
        assert end_time - start_time < 2.0

    @pytest.mark.asyncio
    async def test_network_error_simulation(self, user):
        """Test error handling for network-related errors."""
        
        class NetworkErrorService:
            async def check_permission(self, user, resource, action, context=None):
                raise ConnectionError("Network unreachable")
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                raise TimeoutError("Connection timeout")
        
        network_service = NetworkErrorService()
        
        @require(Permission("network", "test"))
        async def test_function(current_user, rbac_service):
            return "should_not_reach_here"
        
        # Should handle network errors gracefully
        with pytest.raises(HTTPException) as exc_info:
            await test_function(user, network_service)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_fallback_behavior(self, user):
        """Test fallback behavior when primary provider fails."""
        
        class PrimaryService:
            async def check_permission(self, user, resource, action, context=None):
                raise Exception("Primary service down")
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        class FallbackService:
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        primary_service = PrimaryService()
        fallback_service = FallbackService()
        
        @require(Permission("fallback", "test"))
        async def test_function(current_user, rbac_service):
            return f"accessed_by_{current_user.email}"
        
        # Test with primary service (should fail)
        with pytest.raises(HTTPException):
            await test_function(user, primary_service)
        
        # Test with fallback service (should succeed)
        result = await test_function(user, fallback_service)
        assert result == f"accessed_by_{user.email}"

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self, user):
        """Test handling when some operations succeed and others fail."""
        
        class PartialFailureService:
            def __init__(self):
                self.call_count = 0
            
            async def check_permission(self, user, resource, action, context=None):
                self.call_count += 1
                if self.call_count % 2 == 0:
                    raise Exception("Intermittent failure")
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        partial_service = PartialFailureService()
        
        @require(Permission("partial", "test"))
        async def test_function(current_user, rbac_service):
            return f"accessed_by_{current_user.email}"
        
        # First call should succeed
        result1 = await test_function(user, partial_service)
        assert result1 == f"accessed_by_{user.email}"
        
        # Second call should fail
        with pytest.raises(HTTPException):
            await test_function(user, partial_service)


class TestProviderThreadSafety:
    """Tests for provider thread safety and concurrent access.
    
    Validates: Requirements 9.4
    """

    def teardown_method(self):
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.fixture
    def user(self):
        """Create a test user."""
        class TestUser:
            def __init__(self):
                self.id = 1
                self.email = "test@example.com"
                self.role = "user"
        return TestUser()

    @pytest.mark.asyncio
    async def test_concurrent_provider_access(self, user):
        """Test concurrent access to the same provider."""
        
        class ThreadSafeService:
            def __init__(self):
                self.call_count = 0
                self.lock = asyncio.Lock()
            
            async def check_permission(self, user, resource, action, context=None):
                async with self.lock:
                    self.call_count += 1
                    await asyncio.sleep(0.001)  # Simulate work
                    return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        thread_safe_service = ThreadSafeService()
        
        @require(Permission("concurrent", "test"))
        async def concurrent_function(
            request_id: int, 
            current_user, 
            rbac_service
        ):
            return f"request_{request_id}_processed"
        
        # Run many concurrent requests
        tasks = [
            concurrent_function(i, user, thread_safe_service) 
            for i in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 20
        assert all(f"request_{i}_processed" in results for i in range(20))
        assert thread_safe_service.call_count == 20

    def test_provider_registration_thread_safety(self):
        """Test thread safety of provider registration."""
        
        class TestService:
            def __init__(self, service_id: int):
                self.service_id = service_id
            
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        def register_service(service_id: int):
            service = TestService(service_id)
            set_rbac_service(service, f"service_{service_id}")
        
        # Register services from multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(register_service, i) 
                for i in range(10)
            ]
            
            # Wait for all registrations
            for future in as_completed(futures):
                future.result()  # Will raise if there was an exception
        
        # Verify services were registered
        from fastapi_role.rbac import _service_registry
        assert len(_service_registry) >= 10

    @pytest.mark.asyncio
    async def test_context_manager_thread_safety(self, user):
        """Test thread safety of context manager operations."""
        
        class ContextService:
            def __init__(self, service_name: str):
                self.service_name = service_name
            
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        services = [ContextService(f"service_{i}") for i in range(5)]
        results = []
        
        async def use_context_service(service_index: int):
            service = services[service_index]
            
            @require(Permission("context", "test"))
            async def context_function(current_user):
                return f"context_{service.service_name}"
            
            with rbac_service_context(service):
                result = await context_function(user)
                results.append(result)
                return result
        
        # Run multiple context managers concurrently
        tasks = [use_context_service(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # All should complete with correct context
        assert len(results) == 5
        expected_results = [f"context_service_{i}" for i in range(5)]
        assert sorted(results) == sorted(expected_results)

    @pytest.mark.asyncio
    async def test_provider_state_isolation(self, user):
        """Test that provider state is properly isolated between concurrent calls."""
        
        class StatefulService:
            def __init__(self):
                self.current_user = None
                self.current_resource = None
            
            async def check_permission(self, user, resource, action, context=None):
                # Simulate stateful operation
                self.current_user = user.email
                self.current_resource = resource
                await asyncio.sleep(0.001)  # Brief delay
                
                # State should still be consistent
                return (self.current_user == user.email and 
                       self.current_resource == resource)
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        stateful_service = StatefulService()
        
        @require(Permission("state", "test"))
        async def stateful_function(
            resource_name: str, 
            current_user, 
            rbac_service
        ):
            return f"accessed_{resource_name}_by_{current_user.email}"
        
        # Run concurrent requests with different resources
        tasks = [
            stateful_function(f"resource_{i}", user, stateful_service) 
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed (state isolation working)
        assert len(results) == 10
        assert all("accessed_resource_" in result for result in results)


class TestProviderLifecycle:
    """Tests for provider lifecycle management and cleanup.
    
    Validates: Requirements 9.4
    """

    def teardown_method(self):
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    def test_provider_initialization(self):
        """Test proper provider initialization."""
        
        class InitializableService:
            def __init__(self):
                self.initialized = False
                self.connections = []
            
            def initialize(self):
                self.initialized = True
                self.connections.append("database")
                self.connections.append("cache")
            
            async def check_permission(self, user, resource, action, context=None):
                return self.initialized
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return self.initialized
        
        service = InitializableService()
        service.initialize()
        
        set_rbac_service(service)
        
        # Verify initialization
        assert service.initialized
        assert len(service.connections) == 2

    def test_provider_cleanup(self):
        """Test proper provider cleanup."""
        
        class CleanupService:
            def __init__(self):
                self.resources = ["connection1", "connection2", "cache"]
                self.cleaned_up = False
            
            def cleanup(self):
                self.resources.clear()
                self.cleaned_up = True
            
            async def check_permission(self, user, resource, action, context=None):
                return not self.cleaned_up
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return not self.cleaned_up
        
        service = CleanupService()
        set_rbac_service(service, "cleanup_service")
        
        # Simulate cleanup
        service.cleanup()
        
        # Verify cleanup
        assert service.cleaned_up
        assert len(service.resources) == 0

    def test_provider_context_lifecycle(self):
        """Test provider lifecycle within context managers."""
        
        class ContextLifecycleService:
            def __init__(self):
                self.active = False
                self.context_count = 0
            
            def __enter__(self):
                self.active = True
                self.context_count += 1
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.active = False
            
            async def check_permission(self, user, resource, action, context=None):
                return self.active
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return self.active
        
        service = ContextLifecycleService()
        
        # Test context lifecycle
        with service:
            assert service.active
            assert service.context_count == 1
        
        assert not service.active

    def test_provider_resource_management(self):
        """Test provider resource management."""
        
        class ResourceManagedService:
            def __init__(self):
                self.connections = {}
                self.connection_count = 0
            
            def acquire_connection(self, name: str):
                self.connection_count += 1
                self.connections[name] = f"connection_{self.connection_count}"
                return self.connections[name]
            
            def release_connection(self, name: str):
                if name in self.connections:
                    del self.connections[name]
            
            def release_all_connections(self):
                self.connections.clear()
            
            async def check_permission(self, user, resource, action, context=None):
                return len(self.connections) > 0
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return len(self.connections) > 0
        
        service = ResourceManagedService()
        
        # Test resource acquisition
        conn1 = service.acquire_connection("primary")
        conn2 = service.acquire_connection("secondary")
        
        assert len(service.connections) == 2
        assert conn1 != conn2
        
        # Test resource release
        service.release_connection("primary")
        assert len(service.connections) == 1
        
        # Test release all
        service.release_all_connections()
        assert len(service.connections) == 0

    def test_provider_error_recovery(self):
        """Test provider error recovery and restart."""
        
        class RecoverableService:
            def __init__(self):
                self.healthy = True
                self.error_count = 0
                self.recovery_count = 0
            
            def simulate_error(self):
                self.healthy = False
                self.error_count += 1
            
            def recover(self):
                self.healthy = True
                self.recovery_count += 1
            
            async def check_permission(self, user, resource, action, context=None):
                if not self.healthy:
                    raise Exception("Service unhealthy")
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                if not self.healthy:
                    raise Exception("Service unhealthy")
                return True
        
        service = RecoverableService()
        
        # Test error simulation
        service.simulate_error()
        assert not service.healthy
        assert service.error_count == 1
        
        # Test recovery
        service.recover()
        assert service.healthy
        assert service.recovery_count == 1


class TestProviderConfiguration:
    """Tests for provider configuration validation and error reporting.
    
    Validates: Requirements 9.4
    """

    def test_configuration_validation(self):
        """Test validation of provider configuration."""
        
        class ConfigurableService:
            def __init__(self, config: Dict[str, Any]):
                self.config = self._validate_config(config)
            
            def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
                required_keys = ["timeout", "retries", "cache_size"]
                
                for key in required_keys:
                    if key not in config:
                        raise ValueError(f"Missing required configuration: {key}")
                
                if config["timeout"] <= 0:
                    raise ValueError("Timeout must be positive")
                
                if config["retries"] < 0:
                    raise ValueError("Retries cannot be negative")
                
                return config
            
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        # Test valid configuration
        valid_config = {"timeout": 30, "retries": 3, "cache_size": 1000}
        service = ConfigurableService(valid_config)
        assert service.config == valid_config
        
        # Test invalid configuration
        with pytest.raises(ValueError, match="Missing required configuration"):
            ConfigurableService({"timeout": 30})
        
        with pytest.raises(ValueError, match="Timeout must be positive"):
            ConfigurableService({"timeout": -1, "retries": 3, "cache_size": 1000})

    def test_configuration_error_reporting(self):
        """Test error reporting for configuration issues."""
        
        class ErrorReportingService:
            def __init__(self, config: Dict[str, Any]):
                self.config = config
                self.errors = []
                self._validate_and_report_errors()
            
            def _validate_and_report_errors(self):
                if "database_url" not in self.config:
                    self.errors.append("Missing database_url configuration")
                
                if "api_key" not in self.config:
                    self.errors.append("Missing api_key configuration")
                
                if self.config.get("max_connections", 0) <= 0:
                    self.errors.append("max_connections must be positive")
            
            def has_errors(self) -> bool:
                return len(self.errors) > 0
            
            def get_error_report(self) -> str:
                return "; ".join(self.errors)
            
            async def check_permission(self, user, resource, action, context=None):
                if self.has_errors():
                    raise Exception(f"Configuration errors: {self.get_error_report()}")
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        # Test configuration with errors
        config_with_errors = {"max_connections": -1}
        service = ErrorReportingService(config_with_errors)
        
        assert service.has_errors()
        error_report = service.get_error_report()
        assert "Missing database_url" in error_report
        assert "Missing api_key" in error_report
        assert "max_connections must be positive" in error_report

    def test_dynamic_configuration_updates(self):
        """Test dynamic configuration updates."""
        
        class DynamicConfigService:
            def __init__(self, initial_config: Dict[str, Any]):
                self.config = initial_config
                self.config_version = 1
            
            def update_config(self, new_config: Dict[str, Any]):
                self.config.update(new_config)
                self.config_version += 1
            
            def get_config_value(self, key: str, default=None):
                return self.config.get(key, default)
            
            async def check_permission(self, user, resource, action, context=None):
                # Use configuration to determine permission
                return self.get_config_value("allow_all", False)
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        initial_config = {"allow_all": False, "timeout": 30}
        service = DynamicConfigService(initial_config)
        
        # Test initial configuration
        assert service.get_config_value("allow_all") is False
        assert service.config_version == 1
        
        # Test configuration update
        service.update_config({"allow_all": True, "new_setting": "value"})
        assert service.get_config_value("allow_all") is True
        assert service.get_config_value("new_setting") == "value"
        assert service.config_version == 2


class TestProviderMockImplementations:
    """Tests with mock implementations and edge cases.
    
    Validates: Requirements 9.4
    """

    def teardown_method(self):
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.fixture
    def user(self):
        """Create a test user."""
        class TestUser:
            def __init__(self):
                self.id = 1
                self.email = "test@example.com"
                self.role = "user"
        return TestUser()

    @pytest.mark.asyncio
    async def test_always_allow_mock(self, user):
        """Test mock implementation that always allows access."""
        
        class AlwaysAllowMock:
            async def check_permission(self, user, resource, action, context=None):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        mock_service = AlwaysAllowMock()
        
        @require(Permission("mock", "test"))
        async def mock_function(current_user, rbac_service):
            return f"always_allowed_for_{current_user.email}"
        
        result = await mock_function(user, mock_service)
        assert result == f"always_allowed_for_{user.email}"

    @pytest.mark.asyncio
    async def test_always_deny_mock(self, user):
        """Test mock implementation that always denies access."""
        
        class AlwaysDenyMock:
            async def check_permission(self, user, resource, action, context=None):
                return False
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return False
        
        mock_service = AlwaysDenyMock()
        
        @require(Permission("mock", "test"))
        async def mock_function(current_user, rbac_service):
            return "should_not_reach_here"
        
        with pytest.raises(HTTPException) as exc_info:
            await mock_function(user, mock_service)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_conditional_mock(self, user):
        """Test mock implementation with conditional logic."""
        
        class ConditionalMock:
            def __init__(self):
                self.allowed_users = {"test@example.com", "admin@example.com"}
                self.allowed_resources = {"documents", "reports"}
            
            async def check_permission(self, user, resource, action, context=None):
                return (user.email in self.allowed_users and 
                       resource in self.allowed_resources)
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return user.email in self.allowed_users
        
        mock_service = ConditionalMock()
        
        @require(Permission("documents", "read"))
        async def read_document(current_user, rbac_service):
            return f"document_read_by_{current_user.email}"
        
        @require(Permission("secrets", "read"))
        async def read_secrets(current_user, rbac_service):
            return "should_not_reach_here"
        
        # Should allow access to documents
        result = await read_document(user, mock_service)
        assert result == f"document_read_by_{user.email}"
        
        # Should deny access to secrets
        with pytest.raises(HTTPException):
            await read_secrets(user, mock_service)

    @pytest.mark.asyncio
    async def test_stateful_mock(self, user):
        """Test mock implementation that maintains state."""
        
        class StatefulMock:
            def __init__(self):
                self.access_count = {}
                self.max_accesses = 3
            
            async def check_permission(self, user, resource, action, context=None):
                key = f"{user.email}:{resource}:{action}"
                current_count = self.access_count.get(key, 0)
                
                if current_count >= self.max_accesses:
                    return False
                
                self.access_count[key] = current_count + 1
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        mock_service = StatefulMock()
        
        @require(Permission("limited", "access"))
        async def limited_function(current_user, rbac_service):
            return f"access_granted_to_{current_user.email}"
        
        # First few accesses should succeed
        for i in range(3):
            result = await limited_function(user, mock_service)
            assert result == f"access_granted_to_{user.email}"
        
        # Fourth access should fail
        with pytest.raises(HTTPException):
            await limited_function(user, mock_service)

    @pytest.mark.asyncio
    async def test_random_mock(self, user):
        """Test mock implementation with random behavior."""
        
        import random
        
        class RandomMock:
            def __init__(self, success_rate: float = 0.7):
                self.success_rate = success_rate
                random.seed(42)  # For reproducible tests
            
            async def check_permission(self, user, resource, action, context=None):
                return random.random() < self.success_rate
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return random.random() < self.success_rate
        
        mock_service = RandomMock(success_rate=1.0)  # Always succeed for this test
        
        @require(Permission("random", "test"))
        async def random_function(current_user, rbac_service):
            return f"random_access_for_{current_user.email}"
        
        # With success_rate=1.0, should always succeed
        result = await random_function(user, mock_service)
        assert result == f"random_access_for_{user.email}"

    @pytest.mark.asyncio
    async def test_logging_mock(self, user):
        """Test mock implementation that logs all operations."""
        
        class LoggingMock:
            def __init__(self):
                self.permission_logs = []
                self.ownership_logs = []
            
            async def check_permission(self, user, resource, action, context=None):
                log_entry = {
                    "user": user.email,
                    "resource": resource,
                    "action": action,
                    "context": context,
                    "timestamp": time.time()
                }
                self.permission_logs.append(log_entry)
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                log_entry = {
                    "user": user.email,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "timestamp": time.time()
                }
                self.ownership_logs.append(log_entry)
                return True
        
        mock_service = LoggingMock()
        
        @require(Permission("logging", "test"), ResourceOwnership("document", "doc_id"))
        async def logged_function(doc_id: int, current_user, rbac_service):
            return f"logged_access_to_{doc_id}_by_{current_user.email}"
        
        result = await logged_function(123, user, mock_service)
        
        # Verify logging occurred
        assert len(mock_service.permission_logs) == 1
        assert len(mock_service.ownership_logs) == 1
        
        permission_log = mock_service.permission_logs[0]
        assert permission_log["user"] == user.email
        assert permission_log["resource"] == "logging"
        assert permission_log["action"] == "test"
        
        ownership_log = mock_service.ownership_logs[0]
        assert ownership_log["user"] == user.email
        assert ownership_log["resource_type"] == "document"
        assert str(ownership_log["resource_id"]) == "123"  # Convert to string for comparison