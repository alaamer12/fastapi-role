"""Comprehensive integration tests for RBAC system.

This module provides comprehensive integration testing across the entire RBAC system,
including end-to-end workflows, cross-component interactions, and real-world scenarios.

Test Classes:
    TestEndToEndWorkflows: Tests complete user workflows
    TestCrossComponentIntegration: Tests integration between components
    TestRealWorldScenarios: Tests realistic business scenarios
    TestErrorHandlingIntegration: Tests error handling across components
    TestConfigurationIntegration: Tests configuration-driven behavior
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

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
from fastapi_role.core.config import CasbinConfig
from fastapi_role.rbac_service import RBACService
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class MockRBACService:
    """Mock RBAC service for integration testing."""
    
    def __init__(self, permissions_result: bool = True, ownership_result: bool = True):
        self.permissions_result = permissions_result
        self.ownership_result = ownership_result
        self.check_permission = AsyncMock(return_value=permissions_result)
        self.check_resource_ownership = AsyncMock(return_value=ownership_result)
        self.call_history = []
        
        # Track calls for integration testing
        async def tracked_check_permission(user, resource, action, context=None):
            self.call_history.append(("permission", user.email, resource, action))
            return self.permissions_result
            
        async def tracked_check_ownership(user, resource_type, resource_id):
            self.call_history.append(("ownership", user.email, resource_type, resource_id))
            return self.ownership_result
            
        self.check_permission = tracked_check_permission
        self.check_resource_ownership = tracked_check_ownership


class TestEndToEndWorkflows:
    """Tests for complete end-to-end user workflows.
    
    Validates: Requirements 10.3
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
    def admin_user(self):
        """Create an admin user."""
        user = User()
        user.id = 3
        user.email = "admin@example.com"
        user.role = Role.SUPERADMIN.value
        return user

    @pytest.mark.asyncio
    async def test_customer_order_workflow(self, customer_user):
        """Test complete customer order workflow."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Step 1: Browse products (should be allowed)
        @require(Permission("products", "browse"))
        async def browse_products(current_user: User, rbac_service: MockRBACService):
            return ["product1", "product2", "product3"]
        
        # Step 2: Add to cart (should be allowed)
        @require(Permission("cart", "add"))
        async def add_to_cart(product_id: str, current_user: User, rbac_service: MockRBACService):
            return f"added_{product_id}_to_cart"
        
        # Step 3: Create order (should be allowed)
        @require(Permission("orders", "create"))
        async def create_order(current_user: User, rbac_service: MockRBACService):
            return {"order_id": 12345, "status": "created"}
        
        # Step 4: View own order (should be allowed with ownership)
        @require(ResourceOwnership("order"))
        async def view_order(order_id: int, current_user: User, rbac_service: MockRBACService):
            return {"order_id": order_id, "items": ["product1"], "total": 99.99}

        # Execute complete workflow
        products = await browse_products(customer_user, rbac_service)
        cart_result = await add_to_cart("product1", customer_user, rbac_service)
        order = await create_order(customer_user, rbac_service)
        order_details = await view_order(12345, customer_user, rbac_service)
        
        # Verify workflow completed successfully
        assert len(products) == 3
        assert "added_product1_to_cart" == cart_result
        assert order["order_id"] == 12345
        assert order_details["order_id"] == 12345
        
        # Verify all permission checks were made
        assert len(rbac_service.call_history) >= 4

    @pytest.mark.asyncio
    async def test_salesman_quote_workflow(self, salesman_user):
        """Test complete salesman quote workflow."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Step 1: Access customer list
        @require(Permission("customers", "list"))
        async def list_customers(current_user: User, rbac_service: MockRBACService):
            return [{"id": 1, "name": "Customer A"}, {"id": 2, "name": "Customer B"}]
        
        # Step 2: Create quote
        @require(Permission("quotes", "create"))
        async def create_quote(customer_id: int, current_user: User, rbac_service: MockRBACService):
            return {"quote_id": 67890, "customer_id": customer_id, "status": "draft"}
        
        # Step 3: Update quote (with ownership check)
        @require(Permission("quotes", "update"), ResourceOwnership("quote"))
        async def update_quote(quote_id: int, data: dict, current_user: User, rbac_service: MockRBACService):
            return {"quote_id": quote_id, "status": "updated", **data}
        
        # Step 4: Send quote to customer
        @require(Permission("quotes", "send"), ResourceOwnership("quote"))
        async def send_quote(quote_id: int, current_user: User, rbac_service: MockRBACService):
            return {"quote_id": quote_id, "status": "sent", "sent_by": current_user.email}

        # Execute workflow
        customers = await list_customers(salesman_user, rbac_service)
        quote = await create_quote(1, salesman_user, rbac_service)
        updated_quote = await update_quote(67890, {"items": ["item1"]}, salesman_user, rbac_service)
        sent_quote = await send_quote(67890, salesman_user, rbac_service)
        
        # Verify workflow
        assert len(customers) == 2
        assert quote["quote_id"] == 67890
        assert updated_quote["status"] == "updated"
        assert sent_quote["sent_by"] == salesman_user.email

    @pytest.mark.asyncio
    async def test_admin_management_workflow(self, admin_user):
        """Test complete admin management workflow."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Step 1: View system statistics
        @require(Permission("system", "stats"))
        async def view_system_stats(current_user: User, rbac_service: MockRBACService):
            return {"users": 150, "orders": 1200, "revenue": 50000}
        
        # Step 2: Manage users
        @require(Permission("users", "manage"))
        async def manage_user(user_id: int, action: str, current_user: User, rbac_service: MockRBACService):
            return {"user_id": user_id, "action": action, "performed_by": current_user.email}
        
        # Step 3: Generate reports
        @require(Permission("reports", "generate"))
        async def generate_report(report_type: str, current_user: User, rbac_service: MockRBACService):
            return {"report_type": report_type, "generated_at": "2024-01-01", "by": current_user.email}
        
        # Step 4: System configuration
        @require(Permission("system", "configure"))
        async def configure_system(settings: dict, current_user: User, rbac_service: MockRBACService):
            return {"settings": settings, "updated_by": current_user.email}

        # Execute admin workflow
        stats = await view_system_stats(admin_user, rbac_service)
        user_action = await manage_user(123, "suspend", admin_user, rbac_service)
        report = await generate_report("monthly_sales", admin_user, rbac_service)
        config = await configure_system({"max_users": 200}, admin_user, rbac_service)
        
        # Verify admin workflow
        assert stats["users"] == 150
        assert user_action["action"] == "suspend"
        assert report["report_type"] == "monthly_sales"
        assert config["settings"]["max_users"] == 200

    @pytest.mark.asyncio
    async def test_cross_role_collaboration_workflow(self, customer_user, salesman_user, admin_user):
        """Test workflow involving multiple roles collaborating."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Customer creates support ticket
        @require(Permission("support", "create"))
        async def create_support_ticket(issue: str, current_user: User, rbac_service: MockRBACService):
            return {"ticket_id": 555, "issue": issue, "created_by": current_user.email}
        
        # Salesman responds to ticket
        @require(Permission("support", "respond"))
        async def respond_to_ticket(ticket_id: int, response: str, current_user: User, rbac_service: MockRBACService):
            return {"ticket_id": ticket_id, "response": response, "responded_by": current_user.email}
        
        # Admin escalates if needed
        @require(Permission("support", "escalate"))
        async def escalate_ticket(ticket_id: int, current_user: User, rbac_service: MockRBACService):
            return {"ticket_id": ticket_id, "status": "escalated", "escalated_by": current_user.email}

        # Execute collaboration workflow
        ticket = await create_support_ticket("Login issue", customer_user, rbac_service)
        response = await respond_to_ticket(555, "Please try clearing cache", salesman_user, rbac_service)
        escalation = await escalate_ticket(555, admin_user, rbac_service)
        
        # Verify collaboration
        assert ticket["created_by"] == customer_user.email
        assert response["responded_by"] == salesman_user.email
        assert escalation["escalated_by"] == admin_user.email


class TestCrossComponentIntegration:
    """Tests for integration between different RBAC components.
    
    Validates: Requirements 10.1, 10.3
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
    async def test_role_permission_ownership_integration(self, user):
        """Test integration between roles, permissions, and ownership."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Function requiring role, permission, and ownership
        @require(
            Role.CUSTOMER,
            Permission("documents", "edit"),
            ResourceOwnership("document")
        )
        async def edit_document(
            document_id: int, 
            content: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "document_id": document_id,
                "content": content,
                "edited_by": current_user.email
            }

        result = await edit_document(123, "Updated content", user, rbac_service)
        
        # Verify all checks were performed
        assert result["edited_by"] == user.email
        assert len(rbac_service.call_history) >= 2  # Permission and ownership checks

    @pytest.mark.asyncio
    async def test_dynamic_role_with_permissions(self, user):
        """Test integration of dynamic roles with permission system."""
        
        # Create dynamic roles
        CustomRole = create_roles(["viewer", "editor", "admin"])
        
        rbac_service = MockRBACService(permissions_result=True)
        
        @require(CustomRole.EDITOR, Permission("content", "modify"))
        async def modify_content(
            content_id: int, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return f"content_{content_id}_modified_by_{current_user.email}"

        # Update user role to match dynamic role
        user.role = "editor"
        
        result = await modify_content(456, user, rbac_service)
        assert "content_456_modified" in result

    @pytest.mark.asyncio
    async def test_privilege_object_integration(self, user):
        """Test integration using Privilege objects."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Create complex privilege
        complex_privilege = Privilege(
            roles=Role.CUSTOMER,
            permission=Permission("files", "download"),
            resource=ResourceOwnership("file")
        )
        
        @require(complex_privilege)
        async def download_file(
            file_id: int, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "file_id": file_id,
                "download_url": f"https://example.com/files/{file_id}",
                "downloaded_by": current_user.email
            }

        result = await download_file(789, user, rbac_service)
        
        # Verify privilege was properly evaluated
        assert result["file_id"] == 789
        assert result["downloaded_by"] == user.email

    @pytest.mark.asyncio
    async def test_service_injection_with_context_managers(self, user):
        """Test integration of service injection with context managers."""
        
        service1 = MockRBACService(permissions_result=True)
        service2 = MockRBACService(permissions_result=False)
        
        @require(Permission("context", "test"))
        async def context_dependent_function(current_user: User):
            return f"accessed_by_{current_user.email}"

        # Test with allowing service
        with rbac_service_context(service1):
            result1 = await context_dependent_function(user)
            assert "accessed_by_test@example.com" == result1
        
        # Test with denying service
        with rbac_service_context(service2):
            with pytest.raises(HTTPException) as exc_info:
                await context_dependent_function(user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_multiple_decorator_integration(self, user):
        """Test integration of multiple decorators with different requirements."""
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Multiple decorators with OR logic
        @require(Role.SUPERADMIN)  # User doesn't have this
        @require(Permission("backup", "access"), ResourceOwnership("backup"))  # User has this
        async def backup_system(
            backup_id: int, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return f"backup_{backup_id}_accessed_by_{current_user.email}"

        result = await backup_system(999, user, rbac_service)
        assert "backup_999_accessed" in result


class TestRealWorldScenarios:
    """Tests for realistic business scenarios.
    
    Validates: Requirements 10.1, 10.3
    """

    @pytest.fixture
    def ecommerce_user(self):
        """Create an e-commerce user."""
        user = User()
        user.id = 1
        user.email = "customer@shop.com"
        user.role = "premium_customer"
        return user

    @pytest.fixture
    def saas_user(self):
        """Create a SaaS user."""
        user = User()
        user.id = 2
        user.email = "user@tenant.com"
        user.role = "tenant_admin"
        return user

    @pytest.mark.asyncio
    async def test_ecommerce_scenario(self, ecommerce_user):
        """Test realistic e-commerce scenario."""
        
        # Create e-commerce specific roles
        ECommerceRole = create_roles(["customer", "premium_customer", "vendor", "admin"])
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Premium customer exclusive features
        @require(ECommerceRole.PREMIUM_CUSTOMER)
        async def access_premium_features(current_user: User, rbac_service: MockRBACService):
            return {
                "early_access": True,
                "free_shipping": True,
                "priority_support": True,
                "user": current_user.email
            }
        
        # Order management with ownership
        @require(Permission("orders", "manage"), ResourceOwnership("order"))
        async def manage_order(
            order_id: int, 
            action: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "order_id": order_id,
                "action": action,
                "managed_by": current_user.email
            }

        # Execute e-commerce scenario
        premium_features = await access_premium_features(ecommerce_user, rbac_service)
        order_management = await manage_order(12345, "cancel", ecommerce_user, rbac_service)
        
        # Verify e-commerce functionality
        assert premium_features["early_access"] is True
        assert order_management["action"] == "cancel"

    @pytest.mark.asyncio
    async def test_saas_multi_tenant_scenario(self, saas_user):
        """Test realistic SaaS multi-tenant scenario."""
        
        # Create SaaS specific roles
        SaaSRole = create_roles(["user", "admin", "tenant_admin", "super_admin"])
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Tenant administration
        @require(SaaSRole.TENANT_ADMIN)
        async def manage_tenant(action: str, current_user: User, rbac_service: MockRBACService):
            return {
                "tenant_action": action,
                "performed_by": current_user.email,
                "tenant_id": "tenant_123"
            }
        
        # Workspace management with ownership
        @require(Permission("workspaces", "create"), ResourceOwnership("tenant", "tenant_id"))
        async def create_workspace(
            name: str, 
            tenant_id: str,
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "workspace_name": name,
                "created_by": current_user.email,
                "tenant_id": tenant_id
            }

        # Execute SaaS scenario
        tenant_management = await manage_tenant("configure_billing", saas_user, rbac_service)
        workspace_creation = await create_workspace("Development", "tenant_123", saas_user, rbac_service)
        
        # Verify SaaS functionality
        assert tenant_management["tenant_action"] == "configure_billing"
        assert workspace_creation["workspace_name"] == "Development"

    @pytest.mark.asyncio
    async def test_healthcare_scenario(self):
        """Test realistic healthcare scenario."""
        
        # Create healthcare user
        healthcare_user = User()
        healthcare_user.id = 3
        healthcare_user.email = "doctor@hospital.com"
        healthcare_user.role = "physician"
        
        # Create healthcare specific roles
        HealthcareRole = create_roles(["patient", "nurse", "physician", "admin"])
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Patient record access
        @require(HealthcareRole.PHYSICIAN, Permission("patients", "access"))
        async def access_patient_record(
            patient_id: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "patient_id": patient_id,
                "accessed_by": current_user.email,
                "access_level": "full"
            }
        
        # Prescription writing
        @require(Permission("prescriptions", "write"), ResourceOwnership("patient"))
        async def write_prescription(
            patient_id: str, 
            medication: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "patient_id": patient_id,
                "medication": medication,
                "prescribed_by": current_user.email,
                "prescription_id": "RX123456"
            }

        # Execute healthcare scenario
        patient_access = await access_patient_record("PAT001", healthcare_user, rbac_service)
        prescription = await write_prescription("PAT001", "Aspirin 81mg", healthcare_user, rbac_service)
        
        # Verify healthcare functionality
        assert patient_access["access_level"] == "full"
        assert prescription["medication"] == "Aspirin 81mg"

    @pytest.mark.asyncio
    async def test_financial_services_scenario(self):
        """Test realistic financial services scenario."""
        
        # Create financial services user
        financial_user = User()
        financial_user.id = 4
        financial_user.email = "advisor@bank.com"
        financial_user.role = "advisor"
        
        # Create financial specific roles
        FinancialRole = create_roles(["customer", "advisor", "manager", "compliance_officer"])
        
        rbac_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Account access with strict ownership
        @require(FinancialRole.ADVISOR, ResourceOwnership("account"))
        async def access_account(
            account_id: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "account_id": account_id,
                "balance": 50000.00,
                "accessed_by": current_user.email
            }
        
        # Transaction processing
        @require(Permission("transactions", "process"), ResourceOwnership("account"))
        async def process_transaction(
            account_id: str, 
            amount: float, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return {
                "account_id": account_id,
                "amount": amount,
                "processed_by": current_user.email,
                "transaction_id": "TXN789"
            }

        # Execute financial scenario
        account_access = await access_account("ACC001", financial_user, rbac_service)
        transaction = await process_transaction("ACC001", 1000.00, financial_user, rbac_service)
        
        # Verify financial functionality
        assert account_access["balance"] == 50000.00
        assert transaction["amount"] == 1000.00


class TestErrorHandlingIntegration:
    """Tests for error handling across integrated components.
    
    Validates: Requirements 10.3
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
    async def test_cascading_error_handling(self, user):
        """Test error handling when multiple components fail."""
        
        # Service that fails on permission checks
        failing_service = MockRBACService()
        failing_service.check_permission = AsyncMock(side_effect=Exception("Permission service down"))
        
        @require(Permission("test", "action"), ResourceOwnership("resource"))
        async def multi_check_function(current_user: User, rbac_service: MockRBACService):
            return "should_not_reach_here"

        # Should handle permission service failure gracefully
        with pytest.raises(HTTPException) as exc_info:
            await multi_check_function(user, failing_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self, user):
        """Test handling when some checks pass and others fail."""
        
        # Service that passes permission but fails ownership
        partial_service = MockRBACService(permissions_result=True, ownership_result=False)
        
        @require(Permission("partial", "test"), ResourceOwnership("resource"))
        async def partial_check_function(
            resource_id: int, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            return f"resource_{resource_id}_accessed"

        # Should fail due to ownership check failure
        with pytest.raises(HTTPException) as exc_info:
            await partial_check_function(123, user, partial_service)
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, user):
        """Test handling when RBAC service is unavailable."""
        
        @require(Permission("unavailable", "test"))
        async def service_dependent_function(current_user: User):
            return "should_not_reach_here"

        # No service registered - should handle gracefully
        with pytest.raises(HTTPException) as exc_info:
            await service_dependent_function(user)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_malformed_request_handling(self, user):
        """Test handling of malformed requests."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        @require(Permission("malformed", "test"))
        async def strict_function(
            required_param: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            if not required_param:
                raise ValueError("Required parameter missing")
            return f"processed_{required_param}"

        # Test with valid request
        result = await strict_function("valid", user, rbac_service)
        assert result == "processed_valid"
        
        # Test with invalid request (should still pass RBAC but fail business logic)
        with pytest.raises(ValueError):
            await strict_function("", user, rbac_service)


class TestConfigurationIntegration:
    """Tests for configuration-driven behavior integration.
    
    Validates: Requirements 10.1, 10.3
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
    async def test_dynamic_role_configuration_integration(self, user):
        """Test integration with dynamically configured roles."""
        
        # Configuration-driven role creation
        role_config = ["intern", "junior", "senior", "lead", "principal"]
        DynamicRole = create_roles(role_config)
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Update user to match configuration
        user.role = "senior"
        
        @require(DynamicRole.SENIOR)
        async def senior_level_function(current_user: User, rbac_service: MockRBACService):
            return f"senior_access_for_{current_user.email}"

        result = await senior_level_function(user, rbac_service)
        assert "senior_access_for_test@example.com" == result

    @pytest.mark.asyncio
    async def test_permission_configuration_integration(self, user):
        """Test integration with configured permissions."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Configuration-driven permissions
        permission_configs = [
            ("documents", "read"),
            ("documents", "write"),
            ("reports", "generate"),
            ("system", "configure")
        ]
        
        for resource, action in permission_configs:
            @require(Permission(resource, action))
            async def configured_function(
                current_user: User, 
                rbac_service: MockRBACService,
                resource_name: str = resource,
                action_name: str = action
            ):
                return f"{action_name}_{resource_name}_by_{current_user.email}"
            
            result = await configured_function(user, rbac_service)
            assert f"{action}_{resource}_by_test@example.com" == result

    @pytest.mark.asyncio
    async def test_multi_environment_configuration(self, user):
        """Test integration across different environment configurations."""
        
        # Development environment - more permissive
        dev_service = MockRBACService(permissions_result=True, ownership_result=True)
        
        # Production environment - more restrictive
        prod_service = MockRBACService(permissions_result=False, ownership_result=False)
        
        @require(Permission("debug", "access"))
        async def environment_sensitive_function(current_user: User, rbac_service: MockRBACService):
            return f"debug_access_for_{current_user.email}"

        # Should work in development
        result_dev = await environment_sensitive_function(user, dev_service)
        assert "debug_access_for_test@example.com" == result_dev
        
        # Should be restricted in production
        with pytest.raises(HTTPException) as exc_info:
            await environment_sensitive_function(user, prod_service)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_feature_flag_integration(self, user):
        """Test integration with feature flag configurations."""
        
        rbac_service = MockRBACService(permissions_result=True)
        
        # Simulate feature flags
        feature_flags = {
            "new_dashboard": True,
            "beta_features": False,
            "advanced_analytics": True
        }
        
        @require(Permission("features", "access"))
        async def feature_gated_function(
            feature_name: str, 
            current_user: User, 
            rbac_service: MockRBACService
        ):
            if not feature_flags.get(feature_name, False):
                raise HTTPException(status_code=404, detail="Feature not available")
            return f"feature_{feature_name}_accessed_by_{current_user.email}"

        # Test enabled feature
        result1 = await feature_gated_function("new_dashboard", user, rbac_service)
        assert "feature_new_dashboard_accessed" in result1
        
        # Test disabled feature
        with pytest.raises(HTTPException) as exc_info:
            await feature_gated_function("beta_features", user, rbac_service)
        assert exc_info.value.status_code == 404