from unittest.mock import AsyncMock

import pytest

from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.roles import create_roles
from fastapi_role.rbac_service import RBACService

# Create standard roles for testing (matches old hardcoded enum)
TestRole = create_roles(["SUPERADMIN", "SALESMAN", "DATA_ENTRY", "PARTNER", "CUSTOMER"])


@pytest.fixture(scope="session")
def roles():
    """Return the TestRole enum class."""
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
