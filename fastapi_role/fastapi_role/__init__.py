"""FastAPI RBAC - Comprehensive Role-Based Access Control for FastAPI.

This package provides a complete RBAC solution for FastAPI applications using Casbin,
including decorators, template integration, and testing utilities.
"""
from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.roles import create_roles, RoleRegistry
from fastapi_role.rbac import (
    Permission,
    Privilege,
    ResourceOwnership,
    RoleComposition,
    require,
)
from fastapi_role.rbac_service import RBACService


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
]
