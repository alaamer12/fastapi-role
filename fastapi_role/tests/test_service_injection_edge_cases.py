"""Comprehensive tests for RBAC service injection edge cases.

This module tests various edge cases and error scenarios for RBAC service injection,
including missing services, multiple instances, and error handling.

Test Classes:
    TestServiceAvailability: Tests service availability scenarios
    TestMultipleServiceInstances: Tests handling multiple service instances
    TestServiceInjectionErrors: Tests error handling in service injection
    TestBackwardCompatibility: Tests backward compatibility patterns
    TestServiceValidation: Tests service validation and type checking
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, Optional

import pytest
from fastapi import HTTPException

from fastapi_role import (
    Permission, 
    require,
    set_rbac_service,
    get_rbac_service,
    rbac_service_context,
)
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class MockRBACService:
    """Mock RBAC service for testing."""
    
    def __init__(self, name: str = "default", permissions_result: bool = True, ownership_result: bool = True):
        self.name = name
        self.permissions_result = permissions_result
        self.ownership_result = ownership_result
        self.check_permission = AsyncMock(return_value=permissions_result)
        self.check_resource_ownership = AsyncMock(return_value=ownership_result)


class InvalidService:
    """Invalid service that doesn't implement RBAC methods."""
    
    def __init__(self):
        self.some_method = lambda: "not rbac"


class PartialService:
    """Service that only partially implements RBAC interface."""
    
    def __init__(self):
        self.check_permission = AsyncMock(return_value=True)
        # Missing check_resource_ownership method


class TestServiceAvailability:
    """Tests for service availability scenarios.
    
    Validates: Requirements 8.4, 8.5
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def teardown_method(self):
        """Clean up service registry after each test."""
        # Clear the service registry
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.mark.asyncio
    async def test_no_service_available_error(self, user):
        """Test decorator behavior when no service is available."""
        
        @require(Role.CUSTOMER)
        async def function_without_service(current_user: User):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_without_service(user)
        
        assert exc_info.value.status_code == 500
        assert "RBAC service not available" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_service_available_via_registry(self, user):
        """Test service availability via global registry."""
        
        rbac_service = MockRBACService("registry_service")
        set_rbac_service(rbac_service)
        
        @require(Role.CUSTOMER)
        async def function_with_registry_service(current_user: User):
            return f"Success for {current_user.email}"

        result = await function_with_registry_service(user)
        assert "Success for test@example.com" == result

    @pytest.mark.asyncio
    async def test_service_available_via_parameter(self, user):
        """Test service availability via explicit parameter."""
        
        rbac_service = MockRBACService("param_service")
        
        @require(Role.CUSTOMER)
        async def function_with_param_service(current_user: User, rbac_service: MockRBACService):
            return f"Success for {current_user.email}"

        result = await function_with_param_service(user, rbac_service)
        assert "Success for test@example.com" == result

    @pytest.mark.asyncio
    async def test_service_available_via_context(self, user):
        """Test service availability via context manager."""
        
        rbac_service = MockRBACService("context_service")
        
        @require(Role.CUSTOMER)
        async def function_with_context_service(current_user: User):
            return f"Success for {current_user.email}"

        with rbac_service_context(rbac_service):
            result = await function_with_context_service(user)
            assert "Success for test@example.com" == result

    @pytest.mark.asyncio
    async def test_service_priority_explicit_over_registry(self, user):
        """Test that explicit service parameter takes priority over registry."""
        
        registry_service = MockRBACService("registry", permissions_result=False)
        explicit_service = MockRBACService("explicit", permissions_result=True)
        
        set_rbac_service(registry_service)
        
        @require(Permission("test", "action"))
        async def function_with_priority_test(current_user: User, rbac_service: MockRBACService):
            return f"Success for {current_user.email}"

        # Explicit service should be used (and succeed)
        result = await function_with_priority_test(user, explicit_service)
        assert "Success for test@example.com" == result

    @pytest.mark.asyncio
    async def test_service_priority_context_over_registry(self, user):
        """Test that context service takes priority over registry."""
        
        registry_service = MockRBACService("registry", permissions_result=False)
        context_service = MockRBACService("context", permissions_result=True)
        
        set_rbac_service(registry_service)
        
        @require(Permission("test", "action"))
        async def function_with_context_priority(current_user: User):
            return f"Success for {current_user.email}"

        # Context service should be used (and succeed)
        with rbac_service_context(context_service):
            result = await function_with_context_priority(user)
            assert "Success for test@example.com" == result


class TestMultipleServiceInstances:
    """Tests for handling multiple service instances.
    
    Validates: Requirements 8.4, 8.5
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def teardown_method(self):
        """Clean up service registry after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.mark.asyncio
    async def test_multiple_named_services(self, user):
        """Test registration and retrieval of multiple named services."""
        
        service1 = MockRBACService("service1")
        service2 = MockRBACService("service2")
        
        set_rbac_service(service1, "service1")
        set_rbac_service(service2, "service2")
        
        # Test retrieval
        retrieved1 = get_rbac_service("service1")
        retrieved2 = get_rbac_service("service2")
        
        assert retrieved1.name == "service1"
        assert retrieved2.name == "service2"

    @pytest.mark.asyncio
    async def test_default_service_override(self, user):
        """Test that later default service overrides earlier one."""
        
        service1 = MockRBACService("first")
        service2 = MockRBACService("second")
        
        set_rbac_service(service1)  # Default
        set_rbac_service(service2)  # Override default
        
        @require(Role.CUSTOMER)
        async def function_with_default_service(current_user: User):
            return f"Success for {current_user.email}"

        result = await function_with_default_service(user)
        assert "Success for test@example.com" == result

    @pytest.mark.asyncio
    async def test_nested_context_managers(self, user):
        """Test nested context managers with different services."""
        
        service1 = MockRBACService("outer", permissions_result=True)
        service2 = MockRBACService("inner", permissions_result=True)
        
        @require(Permission("test", "action"))
        async def function_with_nested_context(current_user: User):
            # Get the current service to verify which one is active
            current_service = get_rbac_service()
            return f"Success with {current_service.name} for {current_user.email}"

        with rbac_service_context(service1):
            result1 = await function_with_nested_context(user)
            assert "outer" in result1
            
            with rbac_service_context(service2):
                result2 = await function_with_nested_context(user)
                assert "inner" in result2
            
            # Should be back to outer service
            result3 = await function_with_nested_context(user)
            assert "outer" in result3

    @pytest.mark.asyncio
    async def test_concurrent_service_contexts(self, user):
        """Test concurrent execution with different service contexts."""
        
        async def task_with_service(service: MockRBACService, task_id: int):
            @require(Role.CUSTOMER)
            async def protected_task(current_user: User):
                await asyncio.sleep(0.01)  # Simulate work
                current_service = get_rbac_service()
                return f"Task {task_id} with {current_service.name}"
            
            with rbac_service_context(service):
                return await protected_task(user)

        service1 = MockRBACService("service1")
        service2 = MockRBACService("service2")
        service3 = MockRBACService("service3")
        
        # Run tasks concurrently with different services
        tasks = [
            task_with_service(service1, 1),
            task_with_service(service2, 2),
            task_with_service(service3, 3),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Check that each task used the correct service (order may vary due to concurrency)
        result_services = [result.split(" with ")[1] for result in results]
        expected_services = ["service1", "service2", "service3"]
        
        # All expected services should be present (order doesn't matter)
        assert len(results) == 3
        assert set(result_services) == set(expected_services)

    @pytest.mark.asyncio
    async def test_service_isolation_between_functions(self, user):
        """Test that service contexts are properly isolated between functions."""
        
        service1 = MockRBACService("isolated1")
        service2 = MockRBACService("isolated2")
        
        @require(Role.CUSTOMER)
        async def function1(current_user: User):
            service = get_rbac_service()
            return f"Function1 with {service.name}"
        
        @require(Role.CUSTOMER)
        async def function2(current_user: User):
            service = get_rbac_service()
            return f"Function2 with {service.name}"

        # Each function should use its own context service
        with rbac_service_context(service1):
            result1 = await function1(user)
            
        with rbac_service_context(service2):
            result2 = await function2(user)
        
        assert "Function1 with isolated1" == result1
        assert "Function2 with isolated2" == result2


class TestServiceInjectionErrors:
    """Tests for error handling in service injection.
    
    Validates: Requirements 8.5, 8.7
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def teardown_method(self):
        """Clean up service registry after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.mark.asyncio
    async def test_invalid_service_object_error(self, user):
        """Test error when invalid service object is provided."""
        
        invalid_service = InvalidService()
        
        @require(Role.CUSTOMER)
        async def function_with_invalid_service(current_user: User, rbac_service: InvalidService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_invalid_service(user, invalid_service)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_partial_service_interface_error(self, user):
        """Test error when service only partially implements interface."""
        
        partial_service = PartialService()
        
        @require(Role.CUSTOMER)
        async def function_with_partial_service(current_user: User, rbac_service: PartialService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_partial_service(user, partial_service)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_none_service_parameter_error(self, user):
        """Test error when None is passed as service parameter."""
        
        @require(Role.CUSTOMER)
        async def function_with_none_service(current_user: User, rbac_service: None):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_none_service(user, None)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_service_method_exception_handling(self, user):
        """Test handling of exceptions from service methods."""
        
        failing_service = MockRBACService()
        failing_service.check_permission.side_effect = Exception("Service method failed")
        
        @require(Permission("test", "action"))
        async def function_with_failing_service(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_failing_service(user, failing_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_context_manager_invalid_service_error(self, user):
        """Test error when invalid service is used in context manager."""
        
        invalid_service = InvalidService()
        
        with pytest.raises(ValueError) as exc_info:
            with rbac_service_context(invalid_service):
                pass
        
        assert "doesn't implement required RBAC methods" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_registry_nonexistent_name_error(self):
        """Test error when requesting nonexistent service from registry."""
        
        with pytest.raises(ValueError) as exc_info:
            get_rbac_service("nonexistent_service")
        
        assert "No RBAC service registered with name 'nonexistent_service'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_detailed_error_messages(self, user):
        """Test that error messages provide helpful debugging information."""
        
        @require(Role.CUSTOMER)
        async def function_without_any_service(current_user: User):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_without_any_service(user)
        
        error_detail = exc_info.value.detail
        assert "RBAC service not available" in error_detail

    @pytest.mark.asyncio
    async def test_service_injection_parameter_patterns(self, user):
        """Test various parameter patterns for service injection."""
        
        rbac_service = MockRBACService()
        
        # Test different parameter names and positions
        @require(Role.CUSTOMER)
        async def function_with_various_params(
            data: str,
            current_user: User,
            rbac: MockRBACService,  # Alternative name
            extra: str = "default"
        ):
            return f"Success: {data}, {extra}"

        result = await function_with_various_params("test", user, rbac_service, "custom")
        assert "Success: test, custom" == result


class TestBackwardCompatibility:
    """Tests for backward compatibility patterns.
    
    Validates: Requirements 8.5
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    def teardown_method(self):
        """Clean up service registry after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.mark.asyncio
    async def test_global_service_pattern_compatibility(self, user):
        """Test compatibility with existing global service patterns."""
        
        # Simulate old pattern where service was globally available
        rbac_service = MockRBACService("global")
        set_rbac_service(rbac_service)
        
        @require(Role.CUSTOMER)
        async def legacy_function(current_user: User):
            # Old pattern - no explicit service parameter
            return f"Legacy success for {current_user.email}"

        result = await legacy_function(user)
        assert "Legacy success for test@example.com" == result

    @pytest.mark.asyncio
    async def test_mixed_old_new_patterns(self, user):
        """Test mixing old global patterns with new injection patterns."""
        
        global_service = MockRBACService("global")
        explicit_service = MockRBACService("explicit")
        
        set_rbac_service(global_service)
        
        @require(Role.CUSTOMER)
        async def old_style_function(current_user: User):
            return "old_style"
        
        @require(Role.CUSTOMER)
        async def new_style_function(current_user: User, rbac_service: MockRBACService):
            return "new_style"

        # Old style should use global service
        result1 = await old_style_function(user)
        assert "old_style" == result1
        
        # New style should use explicit service
        result2 = await new_style_function(user, explicit_service)
        assert "new_style" == result2

    @pytest.mark.asyncio
    async def test_gradual_migration_support(self, user):
        """Test support for gradual migration from old to new patterns."""
        
        # Start with global service (old pattern)
        global_service = MockRBACService("migration_global")
        set_rbac_service(global_service)
        
        @require(Role.CUSTOMER)
        async def migrating_function(current_user: User, rbac_service: MockRBACService = None):
            # Function that can work with both patterns
            return f"Migration success for {current_user.email}"

        # Should work with global service (old pattern)
        result1 = await migrating_function(user)
        assert "Migration success for test@example.com" == result1
        
        # Should also work with explicit service (new pattern)
        explicit_service = MockRBACService("migration_explicit")
        result2 = await migrating_function(user, explicit_service)
        assert "Migration success for test@example.com" == result2


class TestServiceValidation:
    """Tests for service validation and type checking.
    
    Validates: Requirements 8.4, 8.5
    """

    def teardown_method(self):
        """Clean up service registry after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    def test_service_validation_valid_service(self):
        """Test validation of valid RBAC service."""
        
        from fastapi_role.rbac import _is_rbac_service_like
        
        valid_service = MockRBACService()
        assert _is_rbac_service_like(valid_service) is True

    def test_service_validation_invalid_service(self):
        """Test validation of invalid service objects."""
        
        from fastapi_role.rbac import _is_rbac_service_like
        
        # Test various invalid objects
        assert _is_rbac_service_like(None) is False
        assert _is_rbac_service_like("string") is False
        assert _is_rbac_service_like(123) is False
        assert _is_rbac_service_like([]) is False
        assert _is_rbac_service_like({}) is False

    def test_service_validation_partial_interface(self):
        """Test validation of objects with partial RBAC interface."""
        
        from fastapi_role.rbac import _is_rbac_service_like
        
        partial_service = PartialService()
        assert _is_rbac_service_like(partial_service) is False

    def test_service_validation_non_callable_methods(self):
        """Test validation when methods exist but are not callable."""
        
        from fastapi_role.rbac import _is_rbac_service_like
        
        class NonCallableService:
            check_permission = "not_callable"
            check_resource_ownership = "also_not_callable"
        
        non_callable_service = NonCallableService()
        assert _is_rbac_service_like(non_callable_service) is False

    def test_context_manager_service_validation(self):
        """Test that context manager validates service on entry."""
        
        invalid_service = InvalidService()
        
        with pytest.raises(ValueError) as exc_info:
            with rbac_service_context(invalid_service):
                pass
        
        assert "doesn't implement required RBAC methods" in str(exc_info.value)

    def test_service_registry_validation(self):
        """Test that service registry accepts valid services."""
        
        valid_service = MockRBACService()
        
        # Should not raise any exceptions
        set_rbac_service(valid_service, "test_service")
        retrieved_service = get_rbac_service("test_service")
        
        assert retrieved_service is valid_service