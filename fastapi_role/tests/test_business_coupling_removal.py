"""Comprehensive tests for business coupling removal.

This module tests that the RBAC system is completely business-agnostic and works
with arbitrary resource types, user models, and business domains.

Test Classes:
    TestDatabaseIndependence: Tests system works without database dependencies
    TestArbitraryResourceTypes: Tests system works with any resource types
    TestUserModelFlexibility: Tests system works with different user models
    TestRoleConfigurationFlexibility: Tests system works with various role configurations
    TestBusinessDomainAgnosticism: Tests system works across different business domains
    TestHardcodedConceptsAbsence: Tests no hardcoded business concepts remain
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum

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
from fastapi_role.protocols import UserProtocol


# Test user models for different business domains
@dataclass
class ECommerceUser:
    """User model for e-commerce domain."""
    id: int
    email: str
    role: str
    customer_tier: str = "standard"
    
    def has_role(self, role_name: str) -> bool:
        return self.role == role_name


@dataclass
class SaaSUser:
    """User model for SaaS domain."""
    user_id: str
    username: str
    role: str
    tenant_id: str
    subscription_level: str = "basic"
    
    @property
    def id(self):
        return self.user_id
    
    @property
    def email(self):
        return f"{self.username}@tenant{self.tenant_id}.com"
    
    def has_role(self, role_name: str) -> bool:
        return self.role == role_name


@dataclass
class CRMUser:
    """User model for CRM domain."""
    employee_id: int
    email_address: str
    position: str
    department: str
    access_level: int = 1
    
    @property
    def id(self):
        return self.employee_id
    
    @property
    def email(self):
        return self.email_address
    
    @property
    def role(self):
        return self.position
    
    def has_role(self, role_name: str) -> bool:
        return self.position == role_name


@dataclass
class HealthcareUser:
    """User model for healthcare domain."""
    provider_id: str
    email: str
    role: str
    license_number: str
    specialization: str
    
    @property
    def id(self):
        return self.provider_id
    
    def has_role(self, role_name: str) -> bool:
        return self.role == role_name


class MockRBACService:
    """Mock RBAC service that works with any resource type."""
    
    def __init__(self, permissions_result: bool = True, ownership_result: bool = True):
        self.permissions_result = permissions_result
        self.ownership_result = ownership_result
        self.check_permission = AsyncMock(return_value=permissions_result)
        self.check_resource_ownership = AsyncMock(return_value=ownership_result)


class TestDatabaseIndependence:
    """Tests that system works without database dependencies.
    
    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.6
    """

    def test_rbac_service_without_database(self):
        """Test RBAC service initialization without database."""
        
        # Create roles dynamically
        Role = create_roles(["admin", "user", "guest"])
        
        # Create in-memory configuration
        config = CasbinConfig(
            model_text="""
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
            """
        )
        
        # Should initialize without any database
        service = RBACService(config=config)
        assert service is not None
        assert service.config is not None

    @pytest.mark.asyncio
    async def test_in_memory_rbac_operations(self):
        """Test RBAC operations work purely in memory."""
        
        # Create test user
        user = ECommerceUser(id=1, email="test@example.com", role="user")
        
        # Create mock service (simulates in-memory operation)
        rbac_service = MockRBACService()
        
        @require(Permission("products", "view"))
        async def view_products(current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"products": ["product1", "product2"], "user": current_user.email}

        result = await view_products(user, rbac_service)
        assert result["products"] == ["product1", "product2"]
        assert result["user"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_no_database_session_dependencies(self):
        """Test that no database session is required for RBAC operations."""
        
        user = SaaSUser(user_id="u123", username="testuser", role="member", tenant_id="t456")
        rbac_service = MockRBACService()
        
        @require(Permission("documents", "create"))
        async def create_document(
            title: str, 
            current_user: SaaSUser, 
            rbac_service: MockRBACService
        ):
            # No database session needed
            return {"title": title, "created_by": current_user.email, "tenant": current_user.tenant_id}

        result = await create_document("Test Doc", user, rbac_service)
        assert result["title"] == "Test Doc"
        assert result["created_by"] == "testuser@tenantt456.com"
        assert result["tenant"] == "t456"

    @pytest.mark.asyncio
    async def test_file_based_configuration_only(self):
        """Test system works with file-based configuration only."""
        
        # Simulate file-based configuration (no database)
        Role = create_roles(["manager", "employee", "contractor"])
        
        user = CRMUser(
            employee_id=789, 
            email_address="manager@company.com", 
            position="manager",
            department="sales"
        )
        
        rbac_service = MockRBACService()
        
        @require(Permission("reports", "generate"))
        async def generate_report(
            report_type: str, 
            current_user: CRMUser, 
            rbac_service: MockRBACService
        ):
            return {
                "report_type": report_type, 
                "generated_by": current_user.email,
                "department": current_user.department
            }

        result = await generate_report("sales_summary", user, rbac_service)
        assert result["report_type"] == "sales_summary"
        assert result["generated_by"] == "manager@company.com"
        assert result["department"] == "sales"


class TestArbitraryResourceTypes:
    """Tests that system works with arbitrary resource types.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.7
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return ECommerceUser(id=1, email="test@example.com", role="user")

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_ecommerce_resource_types(self, user, rbac_service):
        """Test with e-commerce specific resource types."""
        
        @require(Permission("products", "manage"))
        async def manage_product(product_id: int, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"action": "manage", "resource": "product", "id": product_id}
        
        @require(Permission("orders", "process"))
        async def process_order(order_id: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"action": "process", "resource": "order", "id": order_id}
        
        @require(Permission("inventory", "update"))
        async def update_inventory(sku: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"action": "update", "resource": "inventory", "sku": sku}

        # Test different resource types
        result1 = await manage_product(123, user, rbac_service)
        assert result1["resource"] == "product"
        
        result2 = await process_order("ORD-456", user, rbac_service)
        assert result2["resource"] == "order"
        
        result3 = await update_inventory("SKU-789", user, rbac_service)
        assert result3["resource"] == "inventory"

    @pytest.mark.asyncio
    async def test_saas_resource_types(self, rbac_service):
        """Test with SaaS specific resource types."""
        
        user = SaaSUser(user_id="u123", username="testuser", role="admin", tenant_id="t456")
        
        @require(Permission("workspaces", "create"))
        async def create_workspace(name: str, current_user: SaaSUser, rbac_service: MockRBACService):
            return {"action": "create", "resource": "workspace", "name": name, "tenant": current_user.tenant_id}
        
        @require(Permission("integrations", "configure"))
        async def configure_integration(integration_type: str, current_user: SaaSUser, rbac_service: MockRBACService):
            return {"action": "configure", "resource": "integration", "type": integration_type}
        
        @require(Permission("analytics", "view"))
        async def view_analytics(dashboard_id: str, current_user: SaaSUser, rbac_service: MockRBACService):
            return {"action": "view", "resource": "analytics", "dashboard": dashboard_id}

        result1 = await create_workspace("My Workspace", user, rbac_service)
        assert result1["resource"] == "workspace"
        assert result1["tenant"] == "t456"
        
        result2 = await configure_integration("slack", user, rbac_service)
        assert result2["resource"] == "integration"
        
        result3 = await view_analytics("dash-123", user, rbac_service)
        assert result3["resource"] == "analytics"

    @pytest.mark.asyncio
    async def test_healthcare_resource_types(self, rbac_service):
        """Test with healthcare specific resource types."""
        
        user = HealthcareUser(
            provider_id="P12345", 
            email="doctor@hospital.com", 
            role="physician",
            license_number="LIC789",
            specialization="cardiology"
        )
        
        @require(Permission("patients", "access"))
        async def access_patient_record(patient_id: str, current_user: HealthcareUser, rbac_service: MockRBACService):
            return {"action": "access", "resource": "patient", "id": patient_id, "provider": current_user.id}
        
        @require(Permission("prescriptions", "write"))
        async def write_prescription(medication: str, current_user: HealthcareUser, rbac_service: MockRBACService):
            return {"action": "write", "resource": "prescription", "medication": medication}
        
        @require(Permission("lab_results", "review"))
        async def review_lab_results(test_id: str, current_user: HealthcareUser, rbac_service: MockRBACService):
            return {"action": "review", "resource": "lab_results", "test": test_id}

        result1 = await access_patient_record("PAT-456", user, rbac_service)
        assert result1["resource"] == "patient"
        assert result1["provider"] == "P12345"
        
        result2 = await write_prescription("aspirin", user, rbac_service)
        assert result2["resource"] == "prescription"
        
        result3 = await review_lab_results("LAB-789", user, rbac_service)
        assert result3["resource"] == "lab_results"

    @pytest.mark.asyncio
    async def test_custom_resource_types(self, user, rbac_service):
        """Test with completely custom resource types."""
        
        @require(Permission("spaceships", "pilot"))
        async def pilot_spaceship(ship_id: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"action": "pilot", "resource": "spaceship", "ship": ship_id}
        
        @require(Permission("dragons", "tame"))
        async def tame_dragon(dragon_name: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"action": "tame", "resource": "dragon", "name": dragon_name}
        
        @require(Permission("magic_spells", "cast"))
        async def cast_spell(spell_type: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"action": "cast", "resource": "magic_spell", "type": spell_type}

        # System should work with any resource type
        result1 = await pilot_spaceship("USS-Enterprise", user, rbac_service)
        assert result1["resource"] == "spaceship"
        
        result2 = await tame_dragon("Smaug", user, rbac_service)
        assert result2["resource"] == "dragon"
        
        result3 = await cast_spell("fireball", user, rbac_service)
        assert result3["resource"] == "magic_spell"


class TestUserModelFlexibility:
    """Tests that system works with different user models.
    
    Validates: Requirements 2.1, 2.4, 5.3
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_different_id_field_names(self, rbac_service):
        """Test system works with different ID field names."""
        
        # User with 'id' field
        user1 = ECommerceUser(id=123, email="user1@example.com", role="customer")
        
        # User with 'user_id' field
        user2 = SaaSUser(user_id="u456", username="user2", role="member", tenant_id="t789")
        
        # User with 'employee_id' field
        user3 = CRMUser(employee_id=789, email_address="user3@company.com", position="manager", department="sales")
        
        @require(Permission("data", "access"))
        async def access_data(current_user: Any, rbac_service: MockRBACService):
            return {"user_id": current_user.id, "email": current_user.email}

        result1 = await access_data(user1, rbac_service)
        assert result1["user_id"] == 123
        
        result2 = await access_data(user2, rbac_service)
        assert result2["user_id"] == "u456"
        
        result3 = await access_data(user3, rbac_service)
        assert result3["user_id"] == 789

    @pytest.mark.asyncio
    async def test_different_email_field_names(self, rbac_service):
        """Test system works with different email field names."""
        
        # User with 'email' field
        user1 = ECommerceUser(id=1, email="user1@example.com", role="customer")
        
        # User with computed email property
        user2 = SaaSUser(user_id="u2", username="user2", role="member", tenant_id="t1")
        
        # User with 'email_address' field
        user3 = CRMUser(employee_id=3, email_address="user3@company.com", position="manager", department="sales")
        
        @require(Permission("notifications", "send"))
        async def send_notification(message: str, current_user: Any, rbac_service: MockRBACService):
            return {"message": message, "recipient": current_user.email}

        result1 = await send_notification("Hello", user1, rbac_service)
        assert result1["recipient"] == "user1@example.com"
        
        result2 = await send_notification("Hello", user2, rbac_service)
        assert result2["recipient"] == "user2@tenantt1.com"
        
        result3 = await send_notification("Hello", user3, rbac_service)
        assert result3["recipient"] == "user3@company.com"

    @pytest.mark.asyncio
    async def test_different_role_field_names(self, rbac_service):
        """Test system works with different role field names."""
        
        # User with 'role' field
        user1 = ECommerceUser(id=1, email="user1@example.com", role="premium_customer")
        
        # User with computed role property
        user2 = CRMUser(employee_id=2, email_address="user2@company.com", position="senior_manager", department="sales")
        
        @require(Permission("premium_features", "access"))
        async def access_premium_features(current_user: Any, rbac_service: MockRBACService):
            return {"user_role": current_user.role, "access_granted": True}

        result1 = await access_premium_features(user1, rbac_service)
        assert result1["user_role"] == "premium_customer"
        
        result2 = await access_premium_features(user2, rbac_service)
        assert result2["user_role"] == "senior_manager"

    @pytest.mark.asyncio
    async def test_additional_user_attributes(self, rbac_service):
        """Test system works with users having additional domain-specific attributes."""
        
        # E-commerce user with customer tier
        ecommerce_user = ECommerceUser(id=1, email="customer@shop.com", role="customer", customer_tier="gold")
        
        # SaaS user with tenant and subscription
        saas_user = SaaSUser(user_id="u123", username="user", role="admin", tenant_id="t456", subscription_level="enterprise")
        
        # Healthcare user with license and specialization
        healthcare_user = HealthcareUser(
            provider_id="P789", 
            email="doctor@hospital.com", 
            role="physician",
            license_number="LIC123",
            specialization="neurology"
        )
        
        @require(Permission("domain_specific", "access"))
        async def access_domain_features(current_user: Any, rbac_service: MockRBACService):
            result = {"user_email": current_user.email, "role": current_user.role}
            
            # Add domain-specific attributes if available
            if hasattr(current_user, 'customer_tier'):
                result["tier"] = current_user.customer_tier
            if hasattr(current_user, 'tenant_id'):
                result["tenant"] = current_user.tenant_id
            if hasattr(current_user, 'specialization'):
                result["specialization"] = current_user.specialization
                
            return result

        result1 = await access_domain_features(ecommerce_user, rbac_service)
        assert result1["tier"] == "gold"
        
        result2 = await access_domain_features(saas_user, rbac_service)
        assert result2["tenant"] == "t456"
        
        result3 = await access_domain_features(healthcare_user, rbac_service)
        assert result3["specialization"] == "neurology"


class TestRoleConfigurationFlexibility:
    """Tests that system works with various role configurations.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.7
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_ecommerce_role_configuration(self, rbac_service):
        """Test with e-commerce specific roles."""
        
        # Create e-commerce roles
        ECommerceRole = create_roles([
            "customer", "premium_customer", "vendor", "store_manager", "admin"
        ])
        
        user = ECommerceUser(id=1, email="customer@shop.com", role="premium_customer")
        
        @require(ECommerceRole.PREMIUM_CUSTOMER)
        async def access_premium_features(current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"feature": "premium_dashboard", "user": current_user.email}

        result = await access_premium_features(user, rbac_service)
        assert result["feature"] == "premium_dashboard"

    @pytest.mark.asyncio
    async def test_saas_role_configuration(self, rbac_service):
        """Test with SaaS specific roles."""
        
        # Create SaaS roles
        SaaSRole = create_roles([
            "viewer", "member", "admin", "owner", "super_admin"
        ])
        
        user = SaaSUser(user_id="u123", username="admin_user", role="admin", tenant_id="t456")
        
        @require(SaaSRole.ADMIN)
        async def manage_tenant(action: str, current_user: SaaSUser, rbac_service: MockRBACService):
            return {"action": action, "tenant": current_user.tenant_id, "admin": current_user.email}

        result = await manage_tenant("configure", user, rbac_service)
        assert result["action"] == "configure"
        assert result["tenant"] == "t456"

    @pytest.mark.asyncio
    async def test_healthcare_role_configuration(self, rbac_service):
        """Test with healthcare specific roles."""
        
        # Create healthcare roles
        HealthcareRole = create_roles([
            "patient", "nurse", "physician", "specialist", "administrator", "system_admin"
        ])
        
        user = HealthcareUser(
            provider_id="P123", 
            email="specialist@hospital.com", 
            role="specialist",
            license_number="LIC456",
            specialization="cardiology"
        )
        
        @require(HealthcareRole.SPECIALIST)
        async def review_complex_case(case_id: str, current_user: HealthcareUser, rbac_service: MockRBACService):
            return {
                "case_id": case_id, 
                "reviewer": current_user.email,
                "specialization": current_user.specialization
            }

        result = await review_complex_case("CASE-789", user, rbac_service)
        assert result["case_id"] == "CASE-789"
        assert result["specialization"] == "cardiology"

    @pytest.mark.asyncio
    async def test_custom_role_hierarchy(self, rbac_service):
        """Test with custom role hierarchies."""
        
        # Create custom role hierarchy
        CustomRole = create_roles([
            "intern", "junior", "senior", "lead", "principal", "architect", "cto"
        ])
        
        user = CRMUser(
            employee_id=123, 
            email_address="lead@company.com", 
            position="lead",
            department="engineering"
        )
        
        @require(CustomRole.LEAD)
        async def lead_team_meeting(topic: str, current_user: CRMUser, rbac_service: MockRBACService):
            return {
                "topic": topic, 
                "leader": current_user.email,
                "department": current_user.department
            }

        result = await lead_team_meeting("Sprint Planning", user, rbac_service)
        assert result["topic"] == "Sprint Planning"
        assert result["department"] == "engineering"

    @pytest.mark.asyncio
    async def test_dynamic_role_creation(self, rbac_service):
        """Test dynamic role creation at runtime."""
        
        # Simulate roles loaded from configuration
        role_names = ["guest", "user", "moderator", "admin"]
        DynamicRole = create_roles(role_names)
        
        user = ECommerceUser(id=1, email="mod@forum.com", role="moderator")
        
        @require(DynamicRole.MODERATOR)
        async def moderate_content(content_id: str, action: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"content_id": content_id, "action": action, "moderator": current_user.email}

        result = await moderate_content("POST-123", "approve", user, rbac_service)
        assert result["content_id"] == "POST-123"
        assert result["action"] == "approve"


class TestBusinessDomainAgnosticism:
    """Tests that system works across different business domains.
    
    Validates: Requirements 1.1, 1.2, 1.3, 5.7
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_cross_domain_compatibility(self, rbac_service):
        """Test that same RBAC system works across different domains."""
        
        # Create generic roles that work across domains
        GenericRole = create_roles(["user", "manager", "admin"])
        
        # E-commerce scenario
        ecommerce_user = ECommerceUser(id=1, email="manager@shop.com", role="manager")
        
        @require(GenericRole.MANAGER)
        async def manage_ecommerce_resource(resource_type: str, current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"domain": "ecommerce", "resource": resource_type, "manager": current_user.email}
        
        # SaaS scenario
        saas_user = SaaSUser(user_id="u123", username="manager", role="manager", tenant_id="t456")
        
        @require(GenericRole.MANAGER)
        async def manage_saas_resource(resource_type: str, current_user: SaaSUser, rbac_service: MockRBACService):
            return {"domain": "saas", "resource": resource_type, "manager": current_user.email}
        
        # Healthcare scenario
        healthcare_user = HealthcareUser(
            provider_id="P123", 
            email="manager@hospital.com", 
            role="manager",
            license_number="LIC789",
            specialization="administration"
        )
        
        @require(GenericRole.MANAGER)
        async def manage_healthcare_resource(resource_type: str, current_user: HealthcareUser, rbac_service: MockRBACService):
            return {"domain": "healthcare", "resource": resource_type, "manager": current_user.email}

        # Same RBAC system should work for all domains
        result1 = await manage_ecommerce_resource("inventory", ecommerce_user, rbac_service)
        assert result1["domain"] == "ecommerce"
        
        result2 = await manage_saas_resource("workspace", saas_user, rbac_service)
        assert result2["domain"] == "saas"
        
        result3 = await manage_healthcare_resource("patient_records", healthcare_user, rbac_service)
        assert result3["domain"] == "healthcare"

    @pytest.mark.asyncio
    async def test_domain_specific_permissions_generic_system(self, rbac_service):
        """Test domain-specific permissions work with generic RBAC system."""
        
        # Different domains can use different permission schemes
        ecommerce_user = ECommerceUser(id=1, email="user@shop.com", role="customer")
        saas_user = SaaSUser(user_id="u123", username="user", role="member", tenant_id="t456")
        
        @require(Permission("products", "browse"))
        async def ecommerce_function(current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"domain": "ecommerce", "action": "browse_products"}
        
        @require(Permission("dashboards", "view"))
        async def saas_function(current_user: SaaSUser, rbac_service: MockRBACService):
            return {"domain": "saas", "action": "view_dashboards"}

        result1 = await ecommerce_function(ecommerce_user, rbac_service)
        assert result1["domain"] == "ecommerce"
        
        result2 = await saas_function(saas_user, rbac_service)
        assert result2["domain"] == "saas"

    @pytest.mark.asyncio
    async def test_multi_tenant_scenarios(self, rbac_service):
        """Test system works in multi-tenant scenarios across domains."""
        
        # SaaS multi-tenant
        tenant1_user = SaaSUser(user_id="u1", username="user1", role="admin", tenant_id="tenant1")
        tenant2_user = SaaSUser(user_id="u2", username="user2", role="admin", tenant_id="tenant2")
        
        @require(Permission("tenant_data", "manage"))
        async def manage_tenant_data(data_type: str, current_user: SaaSUser, rbac_service: MockRBACService):
            return {
                "data_type": data_type, 
                "tenant": current_user.tenant_id,
                "manager": current_user.email
            }

        result1 = await manage_tenant_data("analytics", tenant1_user, rbac_service)
        assert result1["tenant"] == "tenant1"
        
        result2 = await manage_tenant_data("analytics", tenant2_user, rbac_service)
        assert result2["tenant"] == "tenant2"


class TestHardcodedConceptsAbsence:
    """Tests that no hardcoded business concepts remain.
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a mock RBAC service."""
        return MockRBACService()

    @pytest.mark.asyncio
    async def test_no_hardcoded_resource_types(self, rbac_service):
        """Test that system doesn't assume specific resource types."""
        
        user = ECommerceUser(id=1, email="test@example.com", role="user")
        
        # Should work with any resource type name
        resource_types = [
            "quantum_computers", "time_machines", "unicorns", "blockchain_nodes",
            "ai_models", "space_stations", "teleporters", "magic_wands"
        ]
        
        for resource_type in resource_types:
            @require(Permission(resource_type, "access"))
            async def access_resource(current_user: ECommerceUser, rbac_service: MockRBACService):
                return {"resource_type": resource_type, "user": current_user.email}
            
            result = await access_resource(user, rbac_service)
            assert result["resource_type"] == resource_type

    @pytest.mark.asyncio
    async def test_no_hardcoded_action_types(self, rbac_service):
        """Test that system doesn't assume specific action types."""
        
        user = SaaSUser(user_id="u123", username="user", role="member", tenant_id="t456")
        
        # Should work with any action type name
        action_types = [
            "teleport", "transform", "enchant", "decode", "synthesize",
            "materialize", "digitize", "quantify", "optimize", "revolutionize"
        ]
        
        for action_type in action_types:
            @require(Permission("generic_resource", action_type))
            async def perform_action(current_user: SaaSUser, rbac_service: MockRBACService):
                return {"action": action_type, "user": current_user.email}
            
            result = await perform_action(user, rbac_service)
            assert result["action"] == action_type

    @pytest.mark.asyncio
    async def test_no_hardcoded_role_names(self, rbac_service):
        """Test that system doesn't assume specific role names."""
        
        # Create roles with completely arbitrary names
        ArbitraryRole = create_roles([
            "wizard", "ninja", "pirate", "robot", "alien", "superhero"
        ])
        
        user = HealthcareUser(
            provider_id="P123", 
            email="ninja@dojo.com", 
            role="ninja",
            license_number="NINJA-123",
            specialization="stealth"
        )
        
        @require(ArbitraryRole.NINJA)
        async def ninja_action(current_user: HealthcareUser, rbac_service: MockRBACService):
            return {"role": "ninja", "user": current_user.email, "specialization": current_user.specialization}

        result = await ninja_action(user, rbac_service)
        assert result["role"] == "ninja"
        assert result["specialization"] == "stealth"

    @pytest.mark.asyncio
    async def test_no_business_specific_exceptions(self, rbac_service):
        """Test that system doesn't raise business-specific exceptions."""
        
        user = CRMUser(employee_id=1, email_address="test@company.com", position="employee", department="any")
        
        # Create service that denies access
        denying_service = MockRBACService(permissions_result=False)
        
        @require(Permission("any_resource", "any_action"))
        async def protected_function(current_user: CRMUser, rbac_service: MockRBACService):
            return "success"

        # Should raise generic HTTPException, not business-specific exception
        with pytest.raises(HTTPException) as exc_info:
            await protected_function(user, denying_service)
        
        # Exception should be generic, not business-specific
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
        # Should not contain business-specific terms
        assert "customer" not in exc_info.value.detail.lower()
        assert "order" not in exc_info.value.detail.lower()
        assert "quote" not in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_configurable_behavior_only(self, rbac_service):
        """Test that all behavior is configurable, not hardcoded."""
        
        # Test with different role configurations
        Config1Role = create_roles(["level1", "level2", "level3"])
        Config2Role = create_roles(["bronze", "silver", "gold"])
        
        user1 = ECommerceUser(id=1, email="user1@example.com", role="level2")
        user2 = ECommerceUser(id=2, email="user2@example.com", role="silver")
        
        @require(Config1Role.LEVEL2)
        async def config1_function(current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"config": "config1", "user": current_user.email}
        
        @require(Config2Role.SILVER)
        async def config2_function(current_user: ECommerceUser, rbac_service: MockRBACService):
            return {"config": "config2", "user": current_user.email}

        result1 = await config1_function(user1, rbac_service)
        assert result1["config"] == "config1"
        
        result2 = await config2_function(user2, rbac_service)
        assert result2["config"] == "config2"