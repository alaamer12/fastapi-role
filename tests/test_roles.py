"""Unit tests for the Role factory and Casbin configuration system.

This module contains tests to verify that roles are created correctly,
bitwise operations work as expected, and Casbin configurations are
properly generated.
"""

from enum import Enum

from fastapi_role.core.composition import RoleComposition
from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.roles import RoleRegistry, create_roles


class TestRoleFactory:
    """Tests for the create_roles factory and RoleRegistry."""

    # noinspection PyUnresolvedReferences
    def test_create_roles_generates_enum(self):
        """Verifies that create_roles returns a valid Enum with correct values."""
        Role = create_roles(["ADMIN", "USER"])
        assert issubclass(Role, Enum)
        assert Role.ADMIN.value == "admin"
        assert Role.USER.value == "user"

    def test_role_registry(self):
        """Checks if created roles are correctly registered in RoleRegistry."""
        create_roles(["EDITOR", "VIEWER"])
        assert RoleRegistry.is_valid("editor")
        assert RoleRegistry.is_valid("viewer")
        assert not RoleRegistry.is_valid("nonexistent")

    # noinspection PyUnresolvedReferences
    def test_bitwise_operations(self):
        """Tests bitwise OR operations for Role Enums and compositions."""
        Role = create_roles(["A", "B"])
        comp = Role.A | Role.B
        assert isinstance(comp, RoleComposition)
        assert Role.A in comp
        assert Role.B in comp


# noinspection PyUnresolvedReferences
class TestCasbinConfig:
    """Tests for the CasbinConfig configuration class."""

    def test_add_policy(self):
        """Verifies that policies are correctly added to CasbinConfig."""
        config = CasbinConfig()
        Role = create_roles(["ADMIN"])
        config.add_policy(Role.ADMIN, "resource", "read")

        assert len(config.policies) == 1
        policy_list = config.policies[0].to_list()
        assert policy_list == ["admin", "resource", "read", "allow"]

    def test_enforcer_generation(self):
        """Checks if the generated Casbin enforcer correctly evaluates policies."""
        config = CasbinConfig()
        Role = create_roles(["USER"])
        config.add_policy(Role.USER, "data", "read")

        enforcer = config.get_casbin_enforcer()
        assert enforcer.enforce("user", "data", "read") is True
        assert enforcer.enforce("user", "data", "write") is False
