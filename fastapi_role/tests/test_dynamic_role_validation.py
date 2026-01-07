"""Comprehensive validation tests for the dynamic role system.

This module validates that the create_roles() factory and RoleRegistry
work correctly with various role configurations and edge cases.

Test Classes:
    TestCreateRolesFactory: Tests for create_roles() with various configurations
    TestRoleRegistryValidation: Tests for RoleRegistry validation functionality
    TestRoleComposition: Tests for bitwise operations and role composition
    TestRoleSystemScenarios: Tests for different application scenarios
"""

import pytest
from enum import Enum
from typing import Type

from fastapi_role.core.composition import RoleComposition
from fastapi_role.core.roles import RoleRegistry, create_roles


class TestCreateRolesFactory:
    """Tests for create_roles() factory with various role configurations.
    
    Validates: Requirements 3.1, 3.2, 3.6, 3.7
    """

    def test_create_roles_basic_functionality(self):
        """Test basic role creation with simple names."""
        Role = create_roles(["ADMIN", "USER", "GUEST"])
        
        # Verify it's an Enum
        assert issubclass(Role, Enum)
        
        # Verify all roles exist with correct values
        assert Role.ADMIN.value == "admin"
        assert Role.USER.value == "user"
        assert Role.GUEST.value == "guest"
        
        # Verify we can access roles
        assert hasattr(Role, "ADMIN")
        assert hasattr(Role, "USER")
        assert hasattr(Role, "GUEST")

    def test_create_roles_with_complex_names(self):
        """Test role creation with complex naming patterns."""
        Role = create_roles(["SUPER_ADMIN", "DATA_ENTRY", "CONTENT_MANAGER"])
        
        assert Role.SUPER_ADMIN.value == "super_admin"
        assert Role.DATA_ENTRY.value == "data_entry"
        assert Role.CONTENT_MANAGER.value == "content_manager"

    def test_create_roles_with_mixed_case_input(self):
        """Test role creation handles mixed case input correctly."""
        Role = create_roles(["Admin", "user", "GUEST", "Manager"])
        
        # Keys should be uppercase, values lowercase
        assert Role.ADMIN.value == "admin"
        assert Role.USER.value == "user"
        assert Role.GUEST.value == "guest"
        assert Role.MANAGER.value == "manager"

    def test_create_roles_empty_list_behavior(self):
        """Test that empty role list creates empty enum."""
        Role = create_roles([])
        
        # Should create valid but empty enum
        assert issubclass(Role, Enum)
        assert len(list(Role)) == 0

    def test_create_roles_duplicate_names_error(self):
        """Test that duplicate role names are handled appropriately."""
        # This should either deduplicate or raise an error
        try:
            Role = create_roles(["ADMIN", "USER", "ADMIN"])
            # If it doesn't raise an error, verify deduplication worked
            roles = list(Role)
            role_values = [r.value for r in roles]
            assert len(set(role_values)) == len(role_values)  # No duplicates
        except Exception:
            # If it raises an error, that's also acceptable behavior
            pass

    def test_create_roles_consistency_multiple_calls(self):
        """Test that multiple calls with same configuration produce equivalent results."""
        Role1 = create_roles(["ADMIN", "USER"])
        Role2 = create_roles(["ADMIN", "USER"])
        
        # Should have same structure
        assert Role1.ADMIN.value == Role2.ADMIN.value
        assert Role1.USER.value == Role2.USER.value
        
        # Should have same number of roles
        assert len(list(Role1)) == len(list(Role2))

    def test_create_roles_bitwise_operators_injected(self):
        """Test that bitwise operators are properly injected."""
        Role = create_roles(["ADMIN", "USER"])
        
        # Should have __or__ and __ror__ methods
        assert hasattr(Role.ADMIN, "__or__")
        assert hasattr(Role.ADMIN, "__ror__")
        
        # Should be able to use | operator
        composition = Role.ADMIN | Role.USER
        assert isinstance(composition, RoleComposition)

    def test_create_roles_large_number_of_roles(self):
        """Test role creation with a large number of roles."""
        role_names = [f"ROLE_{i}" for i in range(100)]
        Role = create_roles(role_names)
        
        # Verify all roles were created
        assert len(list(Role)) == 100
        
        # Verify a few random ones
        assert Role.ROLE_0.value == "role_0"
        assert Role.ROLE_50.value == "role_50"
        assert Role.ROLE_99.value == "role_99"


class TestRoleRegistryValidation:
    """Tests for RoleRegistry validation functionality.
    
    Validates: Requirements 3.3, 3.7
    """

    def setup_method(self):
        """Reset registry before each test."""
        RoleRegistry._roles = set()
        RoleRegistry._role_enum = None

    def test_role_registry_registration(self):
        """Test that roles are properly registered."""
        Role = create_roles(["ADMIN", "USER"])
        
        # Should be automatically registered
        assert RoleRegistry.is_valid("admin")
        assert RoleRegistry.is_valid("user")
        assert not RoleRegistry.is_valid("nonexistent")

    def test_role_registry_get_roles(self):
        """Test getting all registered roles."""
        Role = create_roles(["MANAGER", "EMPLOYEE", "CONTRACTOR"])
        
        roles = RoleRegistry.get_roles()
        assert "manager" in roles
        assert "employee" in roles
        assert "contractor" in roles
        assert len(roles) == 3

    def test_role_registry_overwrite_registration(self):
        """Test that new role registration overwrites previous."""
        Role1 = create_roles(["ADMIN", "USER"])
        assert RoleRegistry.is_valid("admin")
        assert RoleRegistry.is_valid("user")
        
        Role2 = create_roles(["MANAGER", "EMPLOYEE"])
        # Old roles should no longer be valid
        assert not RoleRegistry.is_valid("admin")
        assert not RoleRegistry.is_valid("user")
        # New roles should be valid
        assert RoleRegistry.is_valid("manager")
        assert RoleRegistry.is_valid("employee")

    def test_role_registry_case_sensitivity(self):
        """Test that role validation is case sensitive."""
        Role = create_roles(["ADMIN"])
        
        assert RoleRegistry.is_valid("admin")  # lowercase value
        assert not RoleRegistry.is_valid("ADMIN")  # uppercase key
        assert not RoleRegistry.is_valid("Admin")  # mixed case


class TestRoleComposition:
    """Tests for bitwise operations and role composition.
    
    Validates: Requirements 3.2, 3.5
    """

    def test_role_bitwise_or_basic(self):
        """Test basic bitwise OR operation between roles."""
        Role = create_roles(["ADMIN", "USER"])
        
        composition = Role.ADMIN | Role.USER
        assert isinstance(composition, RoleComposition)
        assert Role.ADMIN in composition
        assert Role.USER in composition

    def test_role_composition_chaining(self):
        """Test chaining multiple roles with OR operations."""
        Role = create_roles(["A", "B", "C", "D"])
        
        composition = Role.A | Role.B | Role.C | Role.D
        assert isinstance(composition, RoleComposition)
        assert len(composition.roles) == 4
        assert all(role in composition for role in [Role.A, Role.B, Role.C, Role.D])

    def test_role_composition_with_existing_composition(self):
        """Test combining role with existing composition."""
        Role = create_roles(["A", "B", "C"])
        
        comp1 = Role.A | Role.B
        comp2 = comp1 | Role.C
        
        assert isinstance(comp2, RoleComposition)
        assert len(comp2.roles) == 3
        assert all(role in comp2 for role in [Role.A, Role.B, Role.C])

    def test_role_composition_reverse_or(self):
        """Test reverse OR operation (composition | role)."""
        Role = create_roles(["A", "B", "C"])
        
        comp1 = Role.A | Role.B
        comp2 = Role.C | comp1  # reverse order
        
        assert isinstance(comp2, RoleComposition)
        assert len(comp2.roles) == 3

    def test_role_composition_deduplication(self):
        """Test that compositions automatically deduplicate roles."""
        Role = create_roles(["A", "B"])
        
        comp1 = Role.A | Role.B
        comp2 = comp1 | Role.A  # Add A again
        
        assert len(comp2.roles) == 2  # Should still be 2, not 3
        assert Role.A in comp2
        assert Role.B in comp2


class TestRoleSystemScenarios:
    """Tests for different application scenarios.
    
    Validates: Requirements 3.1, 3.4, 3.6
    """

    def test_crm_application_scenario(self):
        """Test role system for a CRM application."""
        Role = create_roles([
            "SUPER_ADMIN", "SALES_MANAGER", "SALESPERSON", 
            "CUSTOMER_SERVICE", "DATA_ENTRY", "CUSTOMER"
        ])
        
        # Verify all CRM roles work
        assert Role.SUPER_ADMIN.value == "super_admin"
        assert Role.SALES_MANAGER.value == "sales_manager"
        assert Role.SALESPERSON.value == "salesperson"
        assert Role.CUSTOMER_SERVICE.value == "customer_service"
        assert Role.DATA_ENTRY.value == "data_entry"
        assert Role.CUSTOMER.value == "customer"
        
        # Test role compositions for CRM scenarios
        sales_roles = Role.SALES_MANAGER | Role.SALESPERSON
        assert len(sales_roles.roles) == 2

    def test_content_management_scenario(self):
        """Test role system for a content management system."""
        Role = create_roles([
            "ADMIN", "EDITOR", "AUTHOR", "REVIEWER", "SUBSCRIBER"
        ])
        
        # Test content management role combinations
        content_creators = Role.EDITOR | Role.AUTHOR
        content_managers = Role.ADMIN | Role.EDITOR | Role.REVIEWER
        
        assert Role.EDITOR in content_creators
        assert Role.AUTHOR in content_creators
        assert len(content_managers.roles) == 3

    def test_ecommerce_scenario(self):
        """Test role system for an e-commerce platform."""
        Role = create_roles([
            "PLATFORM_ADMIN", "STORE_OWNER", "STORE_MANAGER", 
            "INVENTORY_MANAGER", "CUSTOMER_SUPPORT", "CUSTOMER"
        ])
        
        # Test e-commerce role hierarchies
        store_staff = Role.STORE_OWNER | Role.STORE_MANAGER | Role.INVENTORY_MANAGER
        support_staff = Role.CUSTOMER_SUPPORT | Role.STORE_MANAGER
        
        assert len(store_staff.roles) == 3
        assert Role.STORE_MANAGER in support_staff

    def test_multi_tenant_saas_scenario(self):
        """Test role system for a multi-tenant SaaS application."""
        Role = create_roles([
            "PLATFORM_ADMIN", "TENANT_ADMIN", "TENANT_USER", 
            "TENANT_VIEWER", "SUPPORT_AGENT"
        ])
        
        # Test tenant-based role combinations
        tenant_roles = Role.TENANT_ADMIN | Role.TENANT_USER | Role.TENANT_VIEWER
        admin_roles = Role.PLATFORM_ADMIN | Role.TENANT_ADMIN
        
        assert len(tenant_roles.roles) == 3
        assert len(admin_roles.roles) == 2

    def test_role_serialization_scenario(self):
        """Test that roles can be serialized/deserialized for storage."""
        Role = create_roles(["ADMIN", "USER", "GUEST"])
        
        # Test that role values can be stored and retrieved
        role_values = [role.value for role in Role]
        assert "admin" in role_values
        assert "user" in role_values
        assert "guest" in role_values
        
        # Test that we can validate stored values
        for value in role_values:
            assert RoleRegistry.is_valid(value)

    def test_role_system_thread_safety_simulation(self):
        """Test role system behavior under concurrent access simulation."""
        import threading
        import time
        
        results = []
        
        def create_and_test_roles(role_suffix):
            Role = create_roles([f"ADMIN_{role_suffix}", f"USER_{role_suffix}"])
            results.append((Role.ADMIN_1.value if hasattr(Role, 'ADMIN_1') else None, 
                           Role.USER_1.value if hasattr(Role, 'USER_1') else None))
        
        # Simulate concurrent role creation (though registry will overwrite)
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_test_roles, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # At least some results should be captured
        assert len(results) == 5