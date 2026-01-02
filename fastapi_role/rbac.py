"""Role-Based Access Control (RBAC) system using Casbin.

This module provides a comprehensive RBAC system with advanced decorator patterns,
role composition, privilege abstraction, and automatic query filtering.

Features:
    - Casbin policy engine for professional authorization.
    - Multiple decorator patterns with OR/AND logic.
    - Role composition with bitwise operators.
    - Privilege abstraction for reusable authorization.
    - Automatic resource ownership validation.
    - Query filtering for data access control.
    - Template integration for UI permission checks.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, List, Optional, Union

from fastapi import HTTPException

from fastapi_role.core.composition import RoleComposition
from fastapi_role.core.config import CasbinConfig

# Import core components
from fastapi_role.core.roles import RoleRegistry, create_roles
from fastapi_role.protocols import UserProtocol
from fastapi_role.rbac_service import RBACService

# Forward reference for circular import handling if needed,
# though we import RBACService above.

__all__ = [
    "create_roles",
    "RoleRegistry",
    "RoleComposition",
    "CasbinConfig",
    "Permission",
    "ResourceOwnership",
    "Privilege",
    "RBACService",
    "require",
]

logger = logging.getLogger(__name__)


class Permission:
    """Permission definition for resources and actions.

    Represents a specific permission like "configuration:read" or "quote:create".
    Supports context for advanced permission scenarios.
    """

    def __init__(self, resource: str, action: str, context: Optional[dict[str, Any]] = None):
        """Initializes the permission.

        Args:
            resource (str): Resource type (e.g., "configuration", "quote").
            action (str): Action type (e.g., "read", "create", "update", "delete").
            context (Optional[dict[str, Any]]): Optional context for advanced permissions.
        """
        self.resource = resource
        self.action = action
        self.context = context or {}

    def __str__(self) -> str:
        """String representation of permission."""
        return f"{self.resource}:{self.action}"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Permission('{self.resource}', '{self.action}', {self.context})"


class ResourceOwnership:
    """Resource ownership validation.

    Validates that a user owns or has access to a specific resource.
    Automatically extracts resource IDs from function parameters.
    """

    def __init__(self, resource_type: str, id_param: Optional[str] = None):
        """Initializes the resource ownership validator.

        Args:
            resource_type (str): Type of resource (e.g., "configuration", "customer").
            id_param (Optional[str]): Parameter name containing resource ID.
                Defaults to "{resource_type}_id".
        """
        self.resource_type = resource_type
        self.id_param = id_param or f"{resource_type}_id"

    def __str__(self) -> str:
        """String representation of resource ownership."""
        return f"ownership:{self.resource_type}"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"ResourceOwnership('{self.resource_type}', '{self.id_param}')"


class Privilege:
    """Reusable privilege definition bundling role, permission, and resource.

    Enables privilege abstraction for cleaner, more maintainable authorization:
    - Bundle common authorization patterns into reusable objects
    - Combine roles, permissions, and ownership validation
    - Support complex authorization scenarios
    """

    def __init__(
        self,
        roles: Union[Enum, RoleComposition, List[Enum]],
        permission: Permission,
        resource: Optional[ResourceOwnership] = None,
    ):
        """Initializes the privilege.

        Args:
            roles (Union[Enum, RoleComposition, List[Enum]]): Role(s) that have this privilege.
            permission (Permission): Required permission.
            resource (Optional[ResourceOwnership]): Optional resource ownership requirement.
        """
        if isinstance(roles, Enum):
            self.roles = [roles]
        elif isinstance(roles, RoleComposition):
            self.roles = list(roles.roles)
        else:
            self.roles = roles
        self.permission = permission
        self.resource = resource

    def __str__(self) -> str:
        """String representation of privilege."""
        role_names = [role.value for role in self.roles if isinstance(role, Enum)]
        return f"Privilege({role_names}, {self.permission}, {self.resource})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()


def require(*requirements) -> Callable:
    """Advanced decorator supporting multiple authorization patterns.

    Supports patterns like:
    - @require(Role.ADMIN)
    - @require(Permission("resource", "action"))
    - @require(Privilege(...))

    Args:
        *requirements: Authorization requirements (Role Enum, Permission,
            ResourceOwnership, or Privilege).

    Returns:
        Callable: Decorator function that enforces authorization.
    """

    def decorator(func: Callable) -> Callable:
        # Get existing requirements from previous decorators
        existing_requirements = getattr(func, "_rbac_requirements", [])

        # Get the original function (unwrapped) to avoid recursive calls
        original_func = getattr(func, "_rbac_original_func", func)

        # Add new requirements (creates OR relationship with existing)
        all_requirements = existing_requirements + [requirements]

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from function arguments
            user = _extract_user_from_args(args, kwargs)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Evaluate requirements with OR logic between decorator groups
            for requirement_group in all_requirements:
                try:
                    if await _evaluate_requirement_group(
                        user, requirement_group, original_func, args, kwargs
                    ):
                        # At least one requirement group satisfied - allow access
                        logger.debug(f"Access granted to {user.email} for {original_func.__name__}")
                        # Call the original unwrapped function to avoid recursion
                        return await original_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Requirement evaluation error: {e}")
                    continue

            # No requirement group satisfied - deny access
            logger.warning(f"Access denied to {user.email} for {original_func.__name__}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: insufficient privileges for {original_func.__name__}",
            )

        # Store requirements and original function for potential additional decorators
        wrapper._rbac_requirements = all_requirements
        wrapper._rbac_original_func = original_func
        return wrapper

    return decorator


async def _evaluate_requirement_group(
    user: UserProtocol, requirements: tuple, func: Callable, args: tuple, kwargs: dict
) -> bool:
    """Evaluate a single requirement group with AND logic."""
    has_role_requirement = False
    has_permission_requirement = False
    has_ownership_requirement = False

    role_satisfied = True
    permission_satisfied = True
    ownership_satisfied = True

    # We need access to the RBAC service.
    # Current design implies a global 'rbac_service' or one imported from app.core.rbac.
    # In this new design, we should probably resolve it from app dependency or context.
    # For compatibility, we'll try to import it from main location or assume it's injected.
    # For now, we will assume `from fastapi_role.rbac_service import rbac_service` is how it is used?
    # No, typically it is `app.core.rbac.rbac_service`.
    # We will assume a global rbac_service instance is available or passed.
    # Since we can't easily change the signature of the decorator, we rely on the import.

    # FIXME: This is a coupling point.
    # We will assume the service is available at runtime.

    from fastapi_role.rbac_service import rbac_service  # Local import to avoid circular dep

    for requirement in requirements:
        if isinstance(requirement, (Enum, RoleComposition, list)):
            # Check if it's an Enum (Role)
            # Role requirement
            has_role_requirement = True
            role_satisfied = await _check_role_requirement(user, requirement)

        elif isinstance(requirement, Permission):
            # Permission requirement
            has_permission_requirement = True
            permission_satisfied = await _check_permission_requirement(
                rbac_service, user, requirement
            )

        elif isinstance(requirement, ResourceOwnership):
            # Ownership requirement
            has_ownership_requirement = True
            ownership_satisfied = await _check_ownership_requirement(
                rbac_service, user, requirement, func, args, kwargs
            )

        elif isinstance(requirement, Privilege):
            # Privilege requirement (contains role + permission + ownership)
            return await _check_privilege_requirement(
                rbac_service, user, requirement, func, args, kwargs
            )

    # All requirements in group must be satisfied (AND logic)
    final_role_satisfied = role_satisfied if has_role_requirement else True
    final_permission_satisfied = permission_satisfied if has_permission_requirement else True
    final_ownership_satisfied = ownership_satisfied if has_ownership_requirement else True

    return final_role_satisfied and final_permission_satisfied and final_ownership_satisfied


async def _check_role_requirement(
    user: UserProtocol, role_req: Union[Enum, RoleComposition, List[Enum]]
) -> bool:
    """Check role requirement with OR logic for multiple roles."""
    # Use has_role if available (protocol method)
    if hasattr(user, "has_role"):
        # If the user model implements has_role, delegate to it
        # We need to handle the different types of role_req
         if isinstance(role_req, Enum):
            return user.has_role(role_req.value)
         elif isinstance(role_req, RoleComposition):
             return any(user.has_role(role.value) for role in role_req.roles)
         elif isinstance(role_req, list):
             return any(user.has_role(role.value) for role in role_req)

    # Fallback to direct attribute access check
    current_role = user.role  # String value

    if isinstance(role_req, Enum):
        return current_role == role_req.value

    elif isinstance(role_req, RoleComposition):
        return any(current_role == role.value for role in role_req.roles)

    elif isinstance(role_req, list):
        return any(current_role == role.value for role in role_req)

    return False


async def _check_permission_requirement(service, user: UserProtocol, permission: Permission) -> bool:
    """Check permission requirement."""
    return await service.check_permission(
        user, permission.resource, permission.action, permission.context
    )


async def _check_ownership_requirement(
    service, user: UserProtocol, ownership: ResourceOwnership, func: Callable, args: tuple, kwargs: dict
) -> bool:
    """Check resource ownership requirement."""
    # Extract resource ID from function parameters
    resource_id = _extract_resource_id(ownership.id_param, func, args, kwargs)
    if resource_id is None:
        logger.warning(f"Could not extract {ownership.id_param} from {func.__name__} parameters")
        return False

    return await service.check_resource_ownership(user, ownership.resource_type, resource_id)


async def _check_privilege_requirement(
    service, user: UserProtocol, privilege: Privilege, func: Callable, args: tuple, kwargs: dict
) -> bool:
    """Check privilege requirement."""
    # Check role requirement
    role_satisfied = await _check_role_requirement(user, privilege.roles)
    if not role_satisfied:
        return False

    # Check permission requirement
    permission_satisfied = await _check_permission_requirement(service, user, privilege.permission)
    if not permission_satisfied:
        return False

    # Check resource ownership requirement if specified
    if privilege.resource:
        ownership_satisfied = await _check_ownership_requirement(
            service, user, privilege.resource, func, args, kwargs
        )
        if not ownership_satisfied:
            return False

    return True


def _extract_resource_id(
    param_name: str, func: Callable, args: tuple, kwargs: dict
) -> Optional[int]:
    """Extract resource ID from function parameters."""
    # Check keyword arguments first
    if param_name in kwargs:
        return kwargs[param_name]

    # Check positional arguments by parameter name
    import inspect

    try:
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        if param_name in param_names:
            param_index = param_names.index(param_name)
            if param_index < len(args):
                return args[param_index]
    except Exception as e:
        logger.error(f"Error extracting resource ID: {e}")

    return None


def _extract_user_from_args(args: tuple, kwargs: dict) -> Optional[UserProtocol]:
    """Extract user object from function arguments."""
    # Check for 'user' or 'current_user' in kwargs
    if "user" in kwargs:
        return kwargs["user"]
    if "current_user" in kwargs:
        return kwargs["current_user"]

    # Check positional arguments
    for arg in args:
        if _is_user_like(arg):
            return arg

    return None


def _is_user_like(obj: Any) -> bool:
    """Check if object looks like a User model with populated attributes."""
    if obj is None:
        return False
    
    try:
        # Check existence and get values
        obj_id = getattr(obj, "id", None)
        obj_email = getattr(obj, "email", None)
        obj_role = getattr(obj, "role", None)
        
        # All required attributes must be present and not None
        if obj_id is None or obj_email is None or obj_role is None:
            return False
        
        # Attributes should not be callable
        if any(callable(attr) for attr in [obj_id, obj_email, obj_role]):
            return False
        
        # Type checks
        if not isinstance(obj_email, (str, bytes)):
            return False
        
        if not isinstance(obj_role, (str, bytes)):
            return False
        
        return True
        
    except (AttributeError, TypeError):
        return False