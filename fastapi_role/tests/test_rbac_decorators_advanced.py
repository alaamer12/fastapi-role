"""Advanced unit tests for RBAC decorators.

This module tests advanced RBAC decorator patterns including multiple decorators,
role composition, Privilege objects, and context extraction.

Test Classes:
    TestMultipleRequireDecorators: Tests for multiple @require decorators with OR logic
    TestRoleComposition: Tests for role composition with bitwise operators
    TestPrivilegeObjects: Tests for Privilege object functionality
    TestContextExtraction: Tests for context extraction and customer ownership
    TestResourceOwnershipDetection: Tests for automatic parameter detection
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from fastapi_role import Permission, Privilege, ResourceOwnership, require
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class TestMultipleRequireDecorators:
    """Tests for multiple @require decorators with OR logic.

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

    @pytest.fixture
    def salesman_user(self):
        """Create a salesman user."""
        user = User()
        user.id = 2
        user.email = "salesman@example.com"
        user.role = Role.SALESMAN.value
        return user

    @pytest.fixture
    def superadmin_user(self):
        """Create a superadmin user."""
        user = User()
        user.id = 3
        user.email = "admin@example.com"
        user.role = Role.SUPERADMIN.value
        return user

    @pytest.mark.asyncio
    async def test_multiple_decorators_or_logic_success(self, user):
        """Test that multiple decorators use OR logic - success case."""

        @require(Role.SALESMAN)  # User doesn't have this
        @require(Role.CUSTOMER)  # User has this - should succeed
        async def test_function(user: User):
            return "success"

        result = await test_function(user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_decorators_or_logic_failure(self, user):
        """Test that multiple decorators use OR logic - failure case."""

        @require(Role.SALESMAN)  # User doesn't have this
        @require(Role.DATA_ENTRY)  # User doesn't have this either
        async def test_function(user: User):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_multiple_decorators_superadmin_bypass(self, superadmin_user):
        """Test that superadmin bypasses all role requirements."""

        @require(Role.SALESMAN)
        @require(Role.DATA_ENTRY)
        @require(Role.PARTNER)
        async def test_function(user: User):
            return "success"

        result = await test_function(superadmin_user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_decorators_with_permissions(self, user):
        """Test multiple decorators with permission requirements."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock()
        # First permission denied, second permission granted
        mock_service.check_permission.side_effect = [False, True]

        @require(Permission("admin", "access"))  # User likely doesn't have this
        @require(Permission("configuration", "read"))  # User might have this
        async def test_function(user: User, rbac_service):
            return "success"

        result = await test_function(user, mock_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_decorators_mixed_requirements(self, salesman_user):
        """Test multiple decorators with mixed role and permission requirements."""

        @require(Role.CUSTOMER, Permission("customer", "special"))  # AND logic within decorator
        @require(Role.SALESMAN)  # OR logic between decorators
        async def test_function(user: User):
            return "success"

        # Salesman should succeed via second decorator
        result = await test_function(salesman_user)
        assert result == "success"


class TestRoleComposition:
    """Tests for role composition with bitwise operators.

    Validates: Requirements 9.1, 9.2
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.SALESMAN.value
        return user

    @pytest.mark.asyncio
    async def test_role_composition_or_operator(self, user):
        """Test role composition using bitwise OR operator."""
        # Create composed role
        sales_or_partner = Role.SALESMAN | Role.PARTNER

        @require(sales_or_partner)
        async def test_function(user: User):
            return "success"

        # User is salesman, so should succeed
        result = await test_function(user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_role_composition_chaining(self, user):
        """Test chaining multiple roles with OR operator."""
        # Create chained composition
        multi_role = Role.CUSTOMER | Role.SALESMAN | Role.PARTNER

        @require(multi_role)
        async def test_function(user: User):
            return "success"

        # User is salesman, so should succeed
        result = await test_function(user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_role_composition_failure(self):
        """Test role composition failure when user doesn't have any required role."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value

        # Create composition that doesn't include customer
        admin_roles = Role.SALESMAN | Role.DATA_ENTRY

        @require(admin_roles)
        async def test_function(user: User):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(user)

        assert exc_info.value.status_code == 403

    def test_role_composition_contains(self):
        """Test RoleComposition __contains__ method."""
        composition = Role.SALESMAN | Role.PARTNER

        assert Role.SALESMAN in composition
        assert Role.PARTNER in composition
        assert Role.CUSTOMER not in composition

    def test_role_composition_repr(self):
        """Test RoleComposition string representation."""
        composition = Role.SALESMAN | Role.PARTNER
        repr_str = repr(composition)

        assert "RoleComposition" in repr_str
        assert "salesman" in repr_str
        assert "partner" in repr_str


class TestPrivilegeObjects:
    """Tests for Privilege object functionality.

    Validates: Requirements 9.1, 9.3
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.SALESMAN.value
        return user

    @pytest.mark.asyncio
    async def test_privilege_with_single_role(self, user):
        """Test Privilege object with single role."""
        privilege = Privilege(roles=Role.SALESMAN, permission=Permission("quote", "create"))

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock(return_value=True)

        @require(privilege)
        async def test_function(user: User, rbac_service):
            return "success"

        result = await test_function(user, mock_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_privilege_with_role_composition(self, user):
        """Test Privilege object with role composition."""
        sales_roles = Role.SALESMAN | Role.PARTNER
        privilege = Privilege(roles=sales_roles, permission=Permission("customer", "manage"))

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock(return_value=True)

        @require(privilege)
        async def test_function(user: User, rbac_service):
            return "success"

        result = await test_function(user, mock_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_privilege_with_role_list(self, user):
        """Test Privilege object with list of roles."""
        privilege = Privilege(
            roles=[Role.SALESMAN, Role.PARTNER], permission=Permission("quote", "create")
        )

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock(return_value=True)

        @require(privilege)
        async def test_function(user: User, rbac_service):
            return "success"

        result = await test_function(user, mock_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_privilege_with_resource_ownership(self, user):
        """Test Privilege object with resource ownership requirement."""
        privilege = Privilege(
            roles=Role.SALESMAN,
            permission=Permission("customer", "update"),
            resource=ResourceOwnership("customer"),
        )

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock(return_value=True)
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(privilege)
        async def test_function(customer_id: int, user: User, rbac_service):
            return "success"

        result = await test_function(123, user, mock_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_privilege_permission_failure(self, user):
        """Test Privilege object when permission check fails."""
        privilege = Privilege(roles=Role.SALESMAN, permission=Permission("admin", "access"))

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock(return_value=False)

        @require(privilege)
        async def test_function(user: User, rbac_service):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(user, mock_service)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_privilege_ownership_failure(self, user):
        """Test Privilege object when ownership check fails."""
        privilege = Privilege(
            roles=Role.SALESMAN,
            permission=Permission("customer", "update"),
            resource=ResourceOwnership("customer"),
        )

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_permission = AsyncMock(return_value=True)
        mock_service.check_resource_ownership = AsyncMock(return_value=False)  # Ownership denied

        @require(privilege)
        async def test_function(customer_id: int, user: User, rbac_service):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(123, user, mock_service)

        assert exc_info.value.status_code == 403

    def test_privilege_string_representation(self):
        """Test Privilege object string representation."""
        privilege = Privilege(
            roles=[Role.SALESMAN, Role.PARTNER],
            permission=Permission("quote", "create"),
            resource=ResourceOwnership("customer"),
        )

        str_repr = str(privilege)
        assert "Privilege" in str_repr
        assert "salesman" in str_repr
        assert "partner" in str_repr
        assert "quote:create" in str_repr


class TestContextExtraction:
    """Tests for context extraction and customer ownership.

    Validates: Requirements 9.3, 9.5
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
    async def test_context_extraction_from_kwargs(self, user):
        """Test context extraction from keyword arguments."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("configuration"))
        async def test_function(user: User, rbac_service, configuration_id: int):
            return "success"

        result = await test_function(user, mock_service, configuration_id=123)
        assert result == "success"
        mock_service.check_resource_ownership.assert_called_once_with(user, "configuration", 123)

    @pytest.mark.asyncio
    async def test_context_extraction_from_args(self, user):
        """Test context extraction from positional arguments."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("configuration"))
        async def test_function(configuration_id: int, user: User, rbac_service):
            return "success"

        result = await test_function(123, user, mock_service)
        assert result == "success"
        mock_service.check_resource_ownership.assert_called_once_with(user, "configuration", 123)

    @pytest.mark.asyncio
    async def test_context_extraction_custom_param_name(self, user):
        """Test context extraction with custom parameter name."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("customer", "cust_id"))
        async def test_function(cust_id: int, user: User, rbac_service):
            return "success"

        result = await test_function(456, user, mock_service)
        assert result == "success"
        mock_service.check_resource_ownership.assert_called_once_with(user, "customer", 456)

    @pytest.mark.asyncio
    async def test_context_extraction_missing_parameter(self, user):
        """Test context extraction when parameter is missing."""

        @require(ResourceOwnership("configuration"))
        async def test_function(user: User, rbac_service):  # No configuration_id parameter
            return "success"

        # Create mock service (won't be used since parameter is missing)
        mock_service = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await test_function(user, mock_service)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_customer_ownership_validation(self, user):
        """Test customer ownership validation through configuration."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("configuration"))
        async def update_configuration(configuration_id: int, user: User, rbac_service):
            return "updated"

        result = await update_configuration(123, user, mock_service)
        assert result == "updated"
        mock_service.check_resource_ownership.assert_called_once_with(user, "configuration", 123)


class TestResourceOwnershipDetection:
    """Tests for automatic parameter detection in resource ownership.

    Validates: Requirements 9.5
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
    async def test_automatic_parameter_detection_standard(self, user):
        """Test automatic detection of standard parameter names."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("quote"))
        async def create_order(quote_id: int, user: User, rbac_service):
            return "order_created"

        result = await create_order(789, user, mock_service)
        assert result == "order_created"
        mock_service.check_resource_ownership.assert_called_once_with(user, "quote", 789)

    @pytest.mark.asyncio
    async def test_automatic_parameter_detection_multiple_resources(self, user):
        """Test function with multiple resource parameters."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("configuration"))
        @require(ResourceOwnership("customer", "customer_id"))
        async def complex_function(configuration_id: int, customer_id: int, user: User, rbac_service):
            return "success"

        result = await complex_function(123, 456, user, mock_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_parameter_detection_with_mixed_types(self, user):
        """Test parameter detection with mixed parameter types."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("order"))
        async def process_order(order_id: int, status: str, user: User, rbac_service, notes: str = None):
            return f"processed_{status}"

        result = await process_order(999, "completed", user, mock_service, notes="All good")
        assert result == "processed_completed"
        mock_service.check_resource_ownership.assert_called_once_with(user, "order", 999)

    @pytest.mark.asyncio
    async def test_parameter_detection_kwargs_priority(self, user):
        """Test that kwargs take priority over positional args for parameter detection."""

        # Create mock service
        mock_service = AsyncMock()
        mock_service.check_resource_ownership = AsyncMock(return_value=True)

        @require(ResourceOwnership("template"))
        async def apply_template(template_id: int, user: User, rbac_service):
            return "applied"

        # Pass template_id as kwarg (should take priority)
        result = await apply_template(user=user, rbac_service=mock_service, template_id=555)
        assert result == "applied"
        mock_service.check_resource_ownership.assert_called_once_with(user, "template", 555)
