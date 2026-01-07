"""Comprehensive tests for RBAC decorator architecture.

This module provides comprehensive testing for the RBAC decorator system,
covering all supported frameworks, service injection patterns, and edge cases.

Test Classes:
    TestFrameworkCompatibility: Tests decorator with different frameworks
    TestServiceInjectionPatterns: Tests various service injection methods
    TestDecoratorLogicPatterns: Tests OR/AND logic in decorators
    TestEdgeCasesAndErrors: Tests error handling and edge cases
    TestAsyncSyncCompatibility: Tests async/sync function compatibility
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, Optional

import pytest
from fastapi import HTTPException

from fastapi_role import (
    Permission, 
    Privilege, 
    ResourceOwnership, 
    require,
    set_rbac_service,
    get_rbac_service,
    rbac_service_context,
)
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class MockRBACService:
    """Mock RBAC service for testing."""
    
    def __init__(self, permissions_result: bool = True, ownership_result: bool = True):
        self.permissions_result = permissions_result
        self.ownership_result = ownership_result
        self.check_permission = AsyncMock(return_value=permissions_result)
        self.check_resource_ownership = AsyncMock(return_value=ownership_result)


class TestFrameworkCompatibility:
    """Tests for decorator compatibility with different frameworks.
    
    Validates: Requirements 8.1, 8.2, 8.3, 8.6, 8.7
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_fastapi_style_dependency_injection(self, user, rbac_service):
        """Test decorator with FastAPI-style dependency injection."""
        
        @require(Role.CUSTOMER)
        async def fastapi_endpoint(
            user_id: int,
            current_user: User,
            rbac_service: MockRBACService
        ):
            return {"user_id": user_id, "current_user": current_user.email}

        result = await fastapi_endpoint(123, user, rbac_service)
        assert result["user_id"] == 123
        assert result["current_user"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_flask_style_global_service(self, user):
        """Test decorator with Flask-style global service access."""
        
        # Register service globally
        rbac_service = MockRBACService()
        set_rbac_service(rbac_service)
        
        @require(Role.CUSTOMER)
        async def flask_view(current_user: User):
            return {"message": "Flask style access", "user": current_user.email}

        result = await flask_view(user)
        assert result["message"] == "Flask style access"
        assert result["user"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_django_style_class_method(self, user, rbac_service):
        """Test decorator on Django-style class methods."""
        
        class DjangoView:
            @require(Role.CUSTOMER)
            async def get(self, request, current_user: User, rbac_service: MockRBACService):
                return {"method": "GET", "user": current_user.email}
            
            @require(Permission("posts", "create"))
            async def post(self, request, current_user: User, rbac_service: MockRBACService):
                return {"method": "POST", "user": current_user.email}

        view = DjangoView()
        
        # Test GET method
        result = await view.get("mock_request", user, rbac_service)
        assert result["method"] == "GET"
        assert result["user"] == "test@example.com"
        
        # Test POST method
        result = await view.post("mock_request", user, rbac_service)
        assert result["method"] == "POST"
        assert result["user"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_cli_function_protection(self, user, rbac_service):
        """Test decorator protecting CLI functions."""
        
        @require(Role.CUSTOMER)
        async def cli_command(action: str, current_user: User, rbac_service: MockRBACService):
            return f"CLI action: {action} by {current_user.email}"

        result = await cli_command("backup", user, rbac_service)
        assert "CLI action: backup" in result
        assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_background_job_protection(self, user, rbac_service):
        """Test decorator protecting background job functions."""
        
        @require(Permission("jobs", "execute"))
        async def background_job(job_id: int, current_user: User, rbac_service: MockRBACService):
            return {"job_id": job_id, "executed_by": current_user.email}

        result = await background_job(456, user, rbac_service)
        assert result["job_id"] == 456
        assert result["executed_by"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_direct_function_call(self, user, rbac_service):
        """Test decorator on direct function calls (no framework)."""
        
        @require(Role.CUSTOMER, Permission("data", "read"))
        async def business_logic(data_id: int, current_user: User, rbac_service: MockRBACService):
            return {"data_id": data_id, "processed_by": current_user.email}

        result = await business_logic(789, user, rbac_service)
        assert result["data_id"] == 789
        assert result["processed_by"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_test_function_protection(self, user, rbac_service):
        """Test decorator in test scenarios."""
        
        @require(Role.CUSTOMER)
        async def test_helper_function(test_data: str, current_user: User, rbac_service: MockRBACService):
            return f"Test: {test_data} for {current_user.email}"

        result = await test_helper_function("sample_data", user, rbac_service)
        assert "Test: sample_data" in result
        assert "test@example.com" in result


class TestServiceInjectionPatterns:
    """Tests for various service injection patterns.
    
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
    async def test_explicit_rbac_service_parameter(self, user):
        """Test explicit rbac_service parameter injection."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_with_explicit_service(
            data: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return f"Data: {data}, User: {current_user.email}"

        result = await function_with_explicit_service("test_data", user, rbac_service)
        assert "Data: test_data" in result
        assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_explicit_rbac_parameter(self, user):
        """Test explicit rbac parameter injection (alternative name)."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_with_rbac_param(
            data: str, 
            current_user: User, 
            rbac: MockRBACService
        ):
            return f"Data: {data}, User: {current_user.email}"

        result = await function_with_rbac_param("test_data", user, rbac_service)
        assert "Data: test_data" in result
        assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_positional_service_injection(self, user):
        """Test service injection via positional arguments."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_with_positional_service(
            current_user: User, 
            service_obj: MockRBACService,
            data: str
        ):
            return f"Data: {data}, User: {current_user.email}"

        result = await function_with_positional_service(user, rbac_service, "test_data")
        assert "Data: test_data" in result
        assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_global_service_registry(self, user):
        """Test service injection via global registry."""
        
        rbac_service = MockRBACService()
        set_rbac_service(rbac_service, "test_service")
        
        @require(Role.CUSTOMER)
        async def function_with_global_service(current_user: User, data: str):
            return f"Data: {data}, User: {current_user.email}"

        # Should use the globally registered service
        result = await function_with_global_service(user, "test_data")
        assert "Data: test_data" in result
        assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_context_manager_service_injection(self, user):
        """Test service injection via context manager."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_with_context_service(current_user: User, data: str):
            return f"Data: {data}, User: {current_user.email}"

        # Use context manager for scoped service injection
        with rbac_service_context(rbac_service):
            result = await function_with_context_service(user, "test_data")
            assert "Data: test_data" in result
            assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_multiple_service_instances(self, user):
        """Test handling multiple service instances."""
        
        service1 = MockRBACService(permissions_result=True)
        service2 = MockRBACService(permissions_result=False)
        
        set_rbac_service(service1, "service1")
        set_rbac_service(service2, "service2")
        
        @require(Role.CUSTOMER)
        async def function_with_default_service(current_user: User):
            return f"User: {current_user.email}"

        # Should use the default service (last registered or explicitly named)
        with rbac_service_context(service1):
            result = await function_with_default_service(user)
            assert "test@example.com" in result

    @pytest.mark.asyncio
    async def test_service_injection_priority(self, user):
        """Test service injection priority order."""
        
        explicit_service = MockRBACService()
        global_service = MockRBACService()
        
        # Register global service
        set_rbac_service(global_service)
        
        @require(Role.CUSTOMER)
        async def function_with_priority_test(
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return f"User: {current_user.email}"

        # Explicit parameter should take priority over global
        result = await function_with_priority_test(user, explicit_service)
        assert "test@example.com" in result


class TestDecoratorLogicPatterns:
    """Tests for OR/AND logic in decorators.
    
    Validates: Requirements 8.2, 8.3
    """

    @pytest.fixture
    def customer_user(self):
        """Create a customer user."""
        user = User()
        user.id = 1
        user.email = "customer@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.fixture
    def salesman_user(self):
        """Create a salesman user."""
        user = User()
        user.id = 2
        user.email = "salesman@example.com"
        user.role = Role.SALESMAN.value
        return user

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_multiple_decorators_or_logic_success(self, customer_user, rbac_service):
        """Test OR logic between multiple @require decorators - success case."""
        
        @require(Role.SALESMAN)  # User doesn't have this
        @require(Role.CUSTOMER)  # User has this - should succeed
        async def test_function(current_user: User, rbac_service: MockRBACService):
            return "success"

        result = await test_function(customer_user, rbac_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_decorators_or_logic_failure(self, customer_user, rbac_service):
        """Test OR logic between multiple @require decorators - failure case."""
        
        @require(Role.SALESMAN)     # User doesn't have this
        @require(Role.DATA_ENTRY)   # User doesn't have this either
        async def test_function(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(customer_user, rbac_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_single_decorator_and_logic_success(self, salesman_user, rbac_service):
        """Test AND logic within single @require decorator - success case."""
        
        @require(Role.SALESMAN, Permission("quotes", "create"))
        async def test_function(current_user: User, rbac_service: MockRBACService):
            return "success"

        result = await test_function(salesman_user, rbac_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_single_decorator_and_logic_failure(self, customer_user, rbac_service):
        """Test AND logic within single @require decorator - failure case."""
        
        # Customer has role but not permission
        rbac_service.check_permission.return_value = False
        
        @require(Role.CUSTOMER, Permission("admin", "access"))
        async def test_function(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(customer_user, rbac_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_complex_or_and_logic_combination(self, salesman_user, rbac_service):
        """Test complex combination of OR and AND logic."""
        
        @require(Role.CUSTOMER, Permission("customer", "special"))  # AND within decorator
        @require(Role.SALESMAN, Permission("quotes", "create"))     # AND within decorator
        @require(Role.SUPERADMIN)                                   # Single requirement
        async def test_function(current_user: User, rbac_service: MockRBACService):
            return "success"

        # Salesman with quote creation permission should succeed via second decorator
        result = await test_function(salesman_user, rbac_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_privilege_object_and_logic(self, salesman_user, rbac_service):
        """Test AND logic within Privilege objects."""
        
        privilege = Privilege(
            roles=Role.SALESMAN,
            permission=Permission("quotes", "create"),
            resource=ResourceOwnership("customer")
        )
        
        @require(privilege)
        async def test_function(customer_id: int, current_user: User, rbac_service: MockRBACService):
            return "success"

        result = await test_function(123, salesman_user, rbac_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_mixed_requirements_complex_scenario(self, salesman_user, rbac_service):
        """Test mixed requirement types in complex scenario."""
        
        privilege = Privilege(
            roles=[Role.SALESMAN, Role.PARTNER],
            permission=Permission("quotes", "manage")
        )
        
        @require(Role.SUPERADMIN)                           # Simple role
        @require(Permission("admin", "access"))             # Simple permission
        @require(privilege)                                 # Complex privilege
        @require(Role.CUSTOMER, ResourceOwnership("quote")) # Role + ownership
        async def test_function(quote_id: int, current_user: User, rbac_service: MockRBACService):
            return "success"

        # Should succeed via privilege (third decorator)
        result = await test_function(456, salesman_user, rbac_service)
        assert result == "success"


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling.
    
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
    async def test_missing_user_parameter(self):
        """Test decorator behavior when user parameter is missing."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_without_user(data: str, rbac_service: MockRBACService):
            return f"Data: {data}"

        with pytest.raises(HTTPException) as exc_info:
            await function_without_user("test", rbac_service)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_none_user_parameter(self):
        """Test decorator behavior when user parameter is None."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_with_none_user(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_none_user(None, rbac_service)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_user_object(self):
        """Test decorator behavior with invalid user object."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def function_with_invalid_user(current_user: Any, rbac_service: MockRBACService):
            return "success"

        # Pass a string instead of user object
        with pytest.raises(HTTPException) as exc_info:
            await function_with_invalid_user("not_a_user", rbac_service)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_rbac_service(self, user):
        """Test decorator behavior when RBAC service is not available."""
        
        # Clear any existing service registrations
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()
        
        @require(Role.CUSTOMER)
        async def function_without_service(current_user: User):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_without_service(user)
        
        assert exc_info.value.status_code == 500
        assert "RBAC service not available" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_rbac_service(self, user):
        """Test decorator behavior with invalid RBAC service."""
        
        # Clear any existing service registrations
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()
        
        @require(Role.CUSTOMER)
        async def function_with_invalid_service(current_user: User, rbac_service: str):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_invalid_service(user, "not_a_service")
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_rbac_service_method_error(self, user):
        """Test decorator behavior when RBAC service methods raise errors."""
        
        # Create service that raises exceptions
        rbac_service = MockRBACService()
        rbac_service.check_permission.side_effect = Exception("Service error")
        
        @require(Permission("test", "action"))
        async def function_with_failing_service(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_with_failing_service(user, rbac_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_resource_parameter(self, user):
        """Test decorator behavior when required resource parameter is missing."""
        
        rbac_service = MockRBACService()
        
        @require(ResourceOwnership("customer"))
        async def function_without_customer_id(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await function_without_customer_id(user, rbac_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_message_clarity(self, user):
        """Test that error messages are clear and informative."""
        
        rbac_service = MockRBACService(permissions_result=False)
        
        @require(Role.CUSTOMER, Permission("admin", "access"))
        async def admin_function(current_user: User, rbac_service: MockRBACService):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await admin_function(user, rbac_service)
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
        assert "admin_function" in exc_info.value.detail


class TestAsyncSyncCompatibility:
    """Tests for async/sync function compatibility.
    
    Validates: Requirements 8.1, 8.6
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_async_function_protection(self, user, rbac_service):
        """Test decorator on async functions."""
        
        @require(Role.CUSTOMER)
        async def async_function(current_user: User, rbac_service: MockRBACService):
            await asyncio.sleep(0.01)  # Simulate async work
            return f"Async result for {current_user.email}"

        result = await async_function(user, rbac_service)
        assert "Async result for test@example.com" == result

    @pytest.mark.asyncio
    async def test_nested_async_calls(self, user, rbac_service):
        """Test decorator with nested async function calls."""
        
        @require(Role.CUSTOMER)
        async def inner_function(data: str, current_user: User, rbac_service: MockRBACService):
            await asyncio.sleep(0.01)
            return f"Inner: {data} for {current_user.email}"
        
        @require(Permission("outer", "access"))
        async def outer_function(current_user: User, rbac_service: MockRBACService):
            inner_result = await inner_function("test_data", current_user, rbac_service)
            return f"Outer: {inner_result}"

        result = await outer_function(user, rbac_service)
        assert "Outer: Inner: test_data for test@example.com" == result

    @pytest.mark.asyncio
    async def test_concurrent_decorated_functions(self, user, rbac_service):
        """Test concurrent execution of decorated functions."""
        
        @require(Role.CUSTOMER)
        async def concurrent_function(task_id: int, current_user: User, rbac_service: MockRBACService):
            await asyncio.sleep(0.01)
            return f"Task {task_id} for {current_user.email}"

        # Execute multiple functions concurrently
        tasks = [
            concurrent_function(i, user, rbac_service) 
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert f"Task {i} for test@example.com" == result

    @pytest.mark.asyncio
    async def test_async_context_manager_integration(self, user):
        """Test decorator with async context manager for service injection."""
        
        rbac_service = MockRBACService()
        
        @require(Role.CUSTOMER)
        async def context_function(current_user: User):
            return f"Context result for {current_user.email}"

        # Use async context manager pattern
        with rbac_service_context(rbac_service):
            result = await context_function(user)
            assert "Context result for test@example.com" == result

    @pytest.mark.asyncio
    async def test_async_error_propagation(self, user, rbac_service):
        """Test that async errors are properly propagated through decorators."""
        
        @require(Role.CUSTOMER)
        async def error_function(current_user: User, rbac_service: MockRBACService):
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        # The decorator should allow access (user has CUSTOMER role), then the function should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await error_function(user, rbac_service)
        
        assert "Test error" == str(exc_info.value)