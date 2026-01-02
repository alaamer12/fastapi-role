from enum import Enum, auto
from unittest.mock import AsyncMock

import pytest

from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.roles import create_roles
from fastapi_role.rbac_service import RBACService

# Create standard roles for testing (matches old hardcoded enum)
TestRole = create_roles(["SUPERADMIN", "SALESMAN", "DATA_ENTRY", "PARTNER", "CUSTOMER"])


class TestUser:
    """Mock User implementing UserProtocol."""

    def __init__(self, id=1, email="test@example.com", role="customer", full_name="Test User", username="testuser",
                 **kwargs):
        self.id = id
        self.email = email
        self.role = role
        # Optional fields often used in tests
        self.full_name = full_name
        self.username = username
        # Set extra attributes
        for k, v in kwargs.items():
            setattr(self, k, v)

    def has_role(self, role_name: str) -> bool:
        if self.role == "superadmin":
            return True
        return self.role == role_name

    def __repr__(self):
        return f"<User id={self.id} email={self.email} username={self.username} role={self.role}>"


class TestCustomer:
    """Mock Customer for testing."""

    def __init__(self, id=1, email="test@example.com", contact_person="Test User", **kwargs):
        self.id = id
        self.email = email
        self.contact_person = contact_person
        self.customer_type = "residential"
        self.is_active = True
        self.notes = ""
        # Set extra attributes
        for k, v in kwargs.items():
            setattr(self, k, v)


class _TypeRoles(Enum):
    SUPERADMIN = auto()
    SALESMAN = auto()
    DATA_ENTRY = auto()
    PARTNER = auto()
    CUSTOMER = auto()


@pytest.fixture(scope="session")
def roles() -> _TypeRoles:
    """Return the TestRole enum class."""
    # noinspection PyTypeChecker
    return TestRole


@pytest.fixture
def casbin_config(roles):
    """Create a standard CasbinConfig for tests."""
    config = CasbinConfig()

    # Define standard inheritance hierarchy if needed
    # For now, just add basic policies to match old csv
    config.add_policy(roles.SUPERADMIN, "*", "*", "allow")
    config.add_policy(roles.SALESMAN, "*", "*", "allow")
    config.add_policy(roles.DATA_ENTRY, "*", "*", "allow")
    config.add_policy(roles.PARTNER, "*", "*", "allow")
    config.add_policy(roles.CUSTOMER, "configuration", "read", "allow")
    config.add_policy(roles.CUSTOMER, "configuration", "create", "allow")
    config.add_policy(roles.CUSTOMER, "quote", "read", "allow")

    return config


@pytest.fixture
def rbac_service(casbin_config):
    """Create RBACService with test config."""
    db = AsyncMock()
    service = RBACService(db, config=casbin_config)
    return service
