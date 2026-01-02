"""FastAPI RBAC - Comprehensive Role-Based Access Control for FastAPI.

This package provides a complete RBAC solution for FastAPI applications using Casbin,
including decorators, template integration, and testing utilities.
"""

from .rbac import (
    Permission,
    Privilege,
    ResourceOwnership,
    RoleComposition,
    require,
    RBACService,
    RBACQueryFilter,
    create_roles,
    RoleRegistry,
    CasbinConfig,
)
from .rbac_actions import PageAction, TableAction
# Note: rbac_template_helpers might need same treatment if it imported Role
# from .rbac_template_helpers import Can, Has, RBACHelper, RBACTemplateMiddleware

__version__ = "0.1.0"
__all__ = [
    # Core RBAC classes
    "create_roles",
    "RoleRegistry",
    "CasbinConfig",
    "RoleComposition", 
    "Permission",
    "ResourceOwnership",
    "Privilege",
    "require",
    "RBACService",
    "RBACQueryFilter",
    # Actions
    "PageAction",
    "TableAction",
    # Template integration
    # "Can",
    # "Has", 
    # "RBACHelper",
    # "RBACTemplateMiddleware",
]