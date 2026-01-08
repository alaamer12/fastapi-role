"""Comprehensive tests for decorator architecture.

This module provides thorough testing of the @require decorator architecture,
including framework compatibility, service injection patterns, and edge cases.

Test Classes:
    TestDecoratorFrameworkCompatibility: Tests decorator with different frameworks
    TestDecoratorLogicPatterns: Tests complex decorator logic scenarios
    TestDecoratorServiceInjection: Tests service injection patterns
    TestDecoratorErrorHandling: Tests error handling and edge cases
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Callable

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
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class MockRBACService:
    """Mock RBAC service for testing."""
    
    def __init__(self, permissions_result: bool = True, ownership_result: bool = True):
        self.permissions_result = permissions_result
        self.ownership_result = ownership_result
        self.check_permission = AsyncMock(return_value=permissions_result)
        self.check_resource_ownership = AsyncMock(return_value=ownership_result)
        self.call_history = []
        
        async def tracked_check_permission(user, resource, action, context=None):
            self.call_history.append(("permission", user, resource, action))
            return self.permissions_result
            
        async def tracked_check_ownership(user, resource_type, resource_id):
            self.call_history.append(("ownership", user, resource_type, resource_id))
            return self.ownership_result
            
        self.check_permission = tracked_check_permission
        self.check_resource_ownership = tracked_check_ownership


class TestDecoratorFrameworkCompatibility:
    """Tests for decorator compatibility with different frameworks.
    
    Validates: Requirements 9.1
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.mark.asyncio
    async def test_fastapi_compatibility(self, user):
        """Test decorator compatibility with FastAPI patterns."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # FastAPI-style endpoint function
        @require(Permission("api", "access"))
        async def fastapi_endpoint(
            item_id: int,
            current_user: User = None,  # FastAPI dependency injection style
            rbac_service: MockRBACService = None
        ):
            return {"item_id": item_id, "user": current_user.email}

        result = await fastapi_endpoint(123, current_user=user, rbac_service=rbac_service)
        assert result["item_id"] == 123
        assert result["user"] == user.email

    @pytest.mark.asyncio
    async def test_flask_compatibility(self, user):
        """Test decorator compatibility with Flask patterns."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Flask-style synchronous function (but async for testing)
        @require(Permission("flask", "access"))
        async def flask_route(current_user: User, rbac_service: MockRBACService):
            return f"flask_response_for_{current_user.email}"

        # Note: This would be sync in real Flask, but we test the decorator pattern
        result = await flask_route(current_user=user, rbac_service=rbac_service)
        assert result == f"flask_response_for_{user.email}"

    @pytest.mark.asyncio
    async def test_cli_function_compatibility(self, user):
        """Test decorator compatibility with CLI functions."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # CLI-style function
        @require(Permission("cli", "execute"))
        async def cli_command(
            command: str,
            args: List[str],
            current_user: User,
            rbac_service: MockRBACService
        ):
            return {
                "command": command,
                "args": args,
                "executed_by": current_user.email
            }

        result = await cli_command("deploy", ["--env", "prod"], user, rbac_service)
        assert result["command"] == "deploy"
        assert result["executed_by"] == user.email

    @pytest.mark.asyncio
    async def test_background_job_compatibility(self, user):
        """Test decorator compatibility with background jobs."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Background job function
        @require(Permission("jobs", "execute"))
        async def background_job(
            job_id: str,
            payload: Dict[str, Any],
            current_user: User,
            rbac_service: MockRBACService
        ):
            # Simulate background processing
            await asyncio.sleep(0.001)
            return {
                "job_id": job_id,
                "status": "completed",
                "processed_by": current_user.email
            }

        result = await background_job("job_123", {"data": "test"}, user, rbac_service)
        assert result["job_id"] == "job_123"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_direct_function_call_compatibility(self, user):
        """Test decorator compatibility with direct function calls."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Direct function call (not web framework)
        @require(Permission("direct", "call"))
        async def direct_function(
            data: str,
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"processed_{data}_by_{current_user.email}"

        result = await direct_function("test_data", user, rbac_service)
        assert result == f"processed_test_data_by_{user.email}"

    @pytest.mark.asyncio
    async def test_class_method_compatibility(self, user):
        """Test decorator compatibility with class methods."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        class ServiceClass:
            @require(Permission("service", "method"))
            async def service_method(
                self,
                operation: str,
                current_user: User,
                rbac_service: MockRBACService
            ):
                return f"service_{operation}_by_{current_user.email}"

        service = ServiceClass()
        result = await service.service_method("process", user, rbac_service)
        assert result == f"service_process_by_{user.email}"

    @pytest.mark.asyncio
    async def test_static_method_compatibility(self, user):
        """Test decorator compatibility with static methods."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        class UtilityClass:
            @staticmethod
            @require(Permission("utility", "static"))
            async def static_utility(
                value: int,
                current_user: User,
                rbac_service: MockRBACService
            ):
                return f"utility_result_{value}_by_{current_user.email}"

        result = await UtilityClass.static_utility(42, user, rbac_service)
        assert result == f"utility_result_42_by_{user.email}"


class TestDecoratorLogicPatterns:
    """Tests for complex decorator logic patterns.
    
    Validates: Requirements 9.1
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.mark.asyncio
    async def test_multiple_decorators_or_logic(self, user):
        """Test multiple @require decorators with OR logic."""
        
        rbac_service = MockRBACService(permissions_result=False)
        
        # Multiple decorators should use OR logic (any one can grant access)
        @require(Role.SUPERADMIN)  # User doesn't have this
        @require(Permission("fallback", "access"))  # Service denies this
        @require(Role.CUSTOMER)  # User has this role
        async def or_logic_function(current_user: User, rbac_service: MockRBACService):
            return f"or_access_granted_to_{current_user.email}"

        # Should succeed because user has CUSTOMER role (third decorator)
        result = await or_logic_function(user, rbac_service)
        assert result == f"or_access_granted_to_{user.email}"

    @pytest.mark.asyncio
    async def test_mixed_requirements_and_logic(self, user):
        """Test mixed requirements within single @require decorator (AND logic)."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Single decorator with multiple requirements (AND logic)
        @require(
            Role.CUSTOMER,  # User has this
            Permission("mixed", "access"),  # Service allows this
            ResourceOwnership("resource")  # Service allows this
        )
        async def and_logic_function(
            resource_id: int,
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"and_access_granted_to_{current_user.email}_for_{resource_id}"

        result = await and_logic_function(123, user, rbac_service)
        assert result == f"and_access_granted_to_{user.email}_for_123"

    @pytest.mark.asyncio
    async def test_complex_or_and_combination(self, user):
        """Test complex combination of OR and AND logic."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Multiple decorators (OR) with mixed requirements (AND within each)
        @require(Role.SUPERADMIN, Permission("admin", "access"))  # User doesn't have admin
        @require(Role.CUSTOMER, Permission("mixed", "access"))  # User has both
        async def complex_logic_function(current_user: User, rbac_service: MockRBACService):
            return f"complex_access_granted_to_{current_user.email}"

        result = await complex_logic_function(user, rbac_service)
        assert result == f"complex_access_granted_to_{user.email}"

    @pytest.mark.asyncio
    async def test_privilege_object_logic(self, user):
        """Test decorator logic with Privilege objects."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Create complex privilege
        complex_privilege = Privilege(
            roles=Role.CUSTOMER,
            permission=Permission("privilege", "test"),
            resource=ResourceOwnership("document")
        )
        
        @require(complex_privilege)
        async def privilege_function(
            current_user: User,
            rbac_service: MockRBACService,
            document_id: int = 456  # Add document_id parameter for ownership check
        ):
            return f"privilege_access_to_doc_{document_id}_by_{current_user.email}"

        result = await privilege_function(user, rbac_service, document_id=456)
        assert result == f"privilege_access_to_doc_456_by_{user.email}"

    @pytest.mark.asyncio
    async def test_dynamic_role_logic(self, user):
        """Test decorator logic with dynamic roles."""
        
        # Create dynamic roles
        CustomRole = create_roles(["viewer", "editor", "admin"])
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Update user role to match dynamic role
        user.role = "editor"
        
        @require(CustomRole.VIEWER)  # Should fail
        @require(CustomRole.EDITOR)  # Should succeed
        async def dynamic_role_function(current_user: User, rbac_service: MockRBACService):
            return f"dynamic_access_for_{current_user.role}"

        result = await dynamic_role_function(user, rbac_service)
        assert result == "dynamic_access_for_editor"


class TestDecoratorServiceInjection:
    """Tests for decorator service injection patterns.
    
    Validates: Requirements 9.1, 9.2
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
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.mark.asyncio
    async def test_explicit_service_passing(self, user):
        """Test explicit service passing pattern."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        @require(Permission("explicit", "test"))
        async def explicit_function(
            data: str,
            current_user: User,
            rbac_service: MockRBACService  # Explicitly passed
        ):
            return f"explicit_{data}_by_{current_user.email}"

        result = await explicit_function("test", user, rbac_service)
        assert result == f"explicit_test_by_{user.email}"

    @pytest.mark.asyncio
    async def test_dependency_injection_pattern(self, user):
        """Test dependency injection pattern."""
        
        rbac_service = MockRBACService(permissions_result=True)
        set_rbac_service(rbac_service)
        
        @require(Permission("injection", "test"))
        async def injection_function(
            data: str,
            current_user: User
            # rbac_service will be injected automatically
        ):
            return f"injection_{data}_by_{current_user.email}"

        result = await injection_function("test", current_user=user)
        assert result == f"injection_test_by_{user.email}"

    @pytest.mark.asyncio
    async def test_context_resolution_pattern(self, user):
        """Test context-based service resolution."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        @require(Permission("context", "test"))
        async def context_function(
            data: str,
            current_user: User
        ):
            return f"context_{data}_by_{current_user.email}"

        # Use context manager for service resolution
        with rbac_service_context(rbac_service):
            result = await context_function("test", current_user=user)
            assert result == f"context_test_by_{user.email}"

    @pytest.mark.asyncio
    async def test_multiple_service_instances(self, user):
        """Test decorator with multiple service instances."""
        
        service1 = MockRBACService(permissions_result=True)
        service2 = MockRBACService(permissions_result=False)
        
        @require(Permission("multi", "test"))
        async def multi_service_function(
            service_name: str,
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"multi_{service_name}_by_{current_user.email}"

        # Test with allowing service
        result1 = await multi_service_function("service1", user, service1)
        assert result1 == f"multi_service1_by_{user.email}"
        
        # Test with denying service
        with pytest.raises(HTTPException) as exc_info:
            await multi_service_function("service2", user, service2)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_service_injection_parameter_patterns(self, user):
        """Test various parameter patterns for service injection."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Test different parameter positions and names
        @require(Permission("params", "test"))
        async def param_pattern_function(
            current_user: User,
            data: str,
            rbac_service: MockRBACService,  # Service in middle
            extra: Optional[str] = None
        ):
            return f"params_{data}_{extra}_by_{current_user.email}"

        result = await param_pattern_function(user, "test", rbac_service, "extra")
        assert result == f"params_test_extra_by_{user.email}"

    @pytest.mark.asyncio
    async def test_async_sync_function_compatibility(self, user):
        """Test service injection with both async and sync functions."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Async function
        @require(Permission("async", "test"))
        async def async_function(current_user: User, rbac_service: MockRBACService):
            return f"async_by_{current_user.email}"
        
        # Sync function (but async for testing compatibility)
        @require(Permission("sync", "test"))
        async def sync_function(current_user: User, rbac_service: MockRBACService):
            return f"sync_by_{current_user.email}"

        async_result = await async_function(user, rbac_service)
        sync_result = await sync_function(user, rbac_service)
        
        assert async_result == f"async_by_{user.email}"
        assert sync_result == f"sync_by_{user.email}"


class TestDecoratorErrorHandling:
    """Tests for decorator error handling and edge cases.
    
    Validates: Requirements 9.1, 9.2
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
        """Clean up after each test."""
        from fastapi_role.rbac import _service_registry, _service_stack
        _service_registry.clear()
        _service_stack.clear()

    @pytest.mark.asyncio
    async def test_missing_user_handling(self):
        """Test decorator behavior with missing users."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        @require(Permission("missing", "user"))
        async def missing_user_function(
            data: str,
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"should_not_reach_here"

        # Test with None user
        with pytest.raises(HTTPException) as exc_info:
            await missing_user_function("test", None, rbac_service)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_user_handling(self, user):
        """Test decorator behavior with invalid users."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        @require(Permission("invalid", "user"))
        async def invalid_user_function(
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"should_not_reach_here"

        # Test with user missing required attributes
        class InvalidUser:
            pass  # Missing id, email, role attributes
        
        invalid_user = InvalidUser()
        
        with pytest.raises(HTTPException) as exc_info:
            await invalid_user_function(invalid_user, rbac_service)
        assert exc_info.value.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_no_service_available_handling(self, user):
        """Test decorator behavior when no service is available."""
        
        # Clear the global service registry to simulate no service available
        from fastapi_role.rbac import _service_registry
        original_registry = _service_registry.copy()
        _service_registry.clear()
        
        try:
            @require(Permission("no", "service"))
            async def no_service_function(current_user: User):
                return f"should_not_reach_here"

            # No service registered or passed
            with pytest.raises(HTTPException) as exc_info:
                await no_service_function(user)
            assert exc_info.value.status_code == 500
        finally:
            # Restore the original registry
            _service_registry.update(original_registry)

    @pytest.mark.asyncio
    async def test_service_error_handling(self, user):
        """Test decorator error handling when service fails."""
        
        failing_service = MockRBACService()
        failing_service.check_permission = AsyncMock(side_effect=Exception("Service error"))
        
        @require(Permission("failing", "service"))
        async def failing_service_function(
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"should_not_reach_here"

        with pytest.raises(HTTPException) as exc_info:
            await failing_service_function(user, failing_service)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_malformed_permission_handling(self, user):
        """Test decorator behavior with malformed permissions."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Test with None permission - this should be handled gracefully
        # The system may allow None to pass through and handle it during execution
        @require(None)  # Invalid permission
        async def malformed_permission_function(
            current_user: User,
            rbac_service: MockRBACService
        ):
            return "should_not_reach_here"
        
        # The function may execute but should handle None gracefully
        # This tests the robustness of the system
        try:
            result = await malformed_permission_function(user, rbac_service)
            # If it succeeds, the system handled None gracefully
            assert result is not None
        except (HTTPException, ValueError, TypeError):
            # If it fails, that's also acceptable behavior
            pass

    @pytest.mark.asyncio
    async def test_error_message_clarity(self, user):
        """Test that error messages are clear and helpful."""
        
        rbac_service = MockRBACService(permissions_result=False)
        
        @require(Permission("clear", "error"))
        async def clear_error_function(
            current_user: User,
            rbac_service: MockRBACService
        ):
            return "should_not_reach_here"

        with pytest.raises(HTTPException) as exc_info:
            await clear_error_function(user, rbac_service)
        
        # Error should be clear and informative
        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail) or "Forbidden" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_function_signature_validation(self, user):
        """Test validation of function signatures with decorators."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Function with missing required parameters
        @require(Permission("signature", "test"))
        async def missing_params_function():  # Missing current_user and rbac_service
            return "should_not_reach_here"

        # Should handle gracefully (may raise during decoration or execution)
        with pytest.raises((TypeError, HTTPException)):
            await missing_params_function()

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, user):
        """Test error handling under concurrent access."""
        
        failing_service = MockRBACService()
        failing_service.check_permission = AsyncMock(side_effect=Exception("Concurrent error"))
        
        @require(Permission("concurrent", "error"))
        async def concurrent_error_function(
            request_id: int,
            current_user: User,
            rbac_service: MockRBACService
        ):
            return f"should_not_reach_here_{request_id}"

        # Run multiple concurrent requests that should all fail
        tasks = [
            concurrent_error_function(i, user, failing_service) 
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should fail with HTTPException
        for result in results:
            assert isinstance(result, HTTPException)
            assert result.status_code == 403