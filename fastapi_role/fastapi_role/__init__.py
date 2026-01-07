"""FastAPI RBAC - Comprehensive Role-Based Access Control for FastAPI.

This package provides a complete RBAC solution for FastAPI applications using Casbin,
including decorators, template integration, and testing utilities.
"""
from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.resource import ResourceRef, Permission as CorePermission, Privilege as CorePrivilege
from fastapi_role.core.roles import create_roles, RoleRegistry
from fastapi_role.rbac import (
    Permission,
    Privilege,
    ResourceOwnership,
    RoleComposition,
    require,
    set_rbac_service,
    get_rbac_service,
    rbac_service_context,
)
from fastapi_role.rbac_service import RBACService


__version__ = "0.1.0"
__all__ = [
    # Core RBAC classes
    "create_roles",
    "RoleRegistry",
    "CasbinConfig",
    "RoleComposition",
    # Resource classes
    "ResourceRef",
    "CorePermission",
    "CorePrivilege",
    # Decorator classes (for backward compatibility)
    "Permission",
    "ResourceOwnership",
    "Privilege",
    "require",
    # Service injection
    "set_rbac_service",
    "get_rbac_service", 
    "rbac_service_context",
    "RBACService",
]
