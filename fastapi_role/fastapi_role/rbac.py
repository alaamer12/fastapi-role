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
    - Dependency injection support for RBAC service.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, List, Optional, Union

from fastapi import HTTPException

from fastapi_role.core.composition import RoleComposition

# Import core components
from fastapi_role.protocols import UserProtocol

# Service registry for dependency injection
_service_registry: dict[str, Any] = {}
_service_stack: list[Any] = []  # Stack for nested service contexts


__all__ = [
    "Permission",
    "ResourceOwnership", 
    "Privilege",
    "require",
    "set_rbac_service",
    "get_rbac_service",
    "rbac_service_context",
]

logger = logging.getLogger(__name__)


def set_rbac_service(service: Any, name: str = "default") -> None:
    """Register an RBAC service instance for dependency injection.
    
    Args:
        service: The RBAC service instance
        name: Optional name for the service (default: "default")
    """
    _service_registry[name] = service


def get_rbac_service(name: str = "default") -> Any:
    """Get a registered RBAC service instance.
    
    Args:
        name: Name of the service to retrieve (default: "default")
        
    Returns:
        The registered RBAC service instance
        
    Raises:
        ValueError: If no service is registered with the given name
    """
    # Check service stack first (for context managers)
    if _service_stack:
        return _service_stack[-1]
        
    if name not in _service_registry:
        raise ValueError(f"No RBAC service registered with name '{name}'")
    return _service_registry[name]


class rbac_service_context:
    """Context manager for scoped RBAC service injection.
    
    This allows temporary service injection that automatically cleans up:
    
    Example:
        with rbac_service_context(my_service):
            # All @require decorators in this block will use my_service
            result = protected_function()
    """
    
    def __init__(self, service: Any):
        """Initialize context with service.
        
        Args:
            service: RBAC service instance to use in this context
            
        Raises:
            ValueError: If service doesn't look like an RBAC service
        """
        if not _is_rbac_service_like(service):
            raise ValueError("Provided service doesn't implement required RBAC methods")
        self.service = service
    
    def __enter__(self):
        """Enter context and push service onto stack."""
        _service_stack.append(self.service)
        return self.service
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and pop service from stack."""
        if _service_stack:
            _service_stack.pop()


def _get_rbac_service_from_context(args: tuple, kwargs: dict) -> Any:
    """Extract RBAC service from function arguments or registry.
    
    Supports multiple injection patterns by priority:
    1. Explicit service parameter (rbac_service, rbac)
    2. Service registry lookup (set via set_rbac_service())
    3. Service-like object in positional arguments
    
    Args:
        args: Function positional arguments
        kwargs: Function keyword arguments
        
    Returns:
        RBAC service instance
        
    Raises:
        ValueError: If no RBAC service is available through any pattern
    """
    # Pattern 1: Check for explicit service in kwargs
    for param_name in ["rbac_service", "rbac"]:
        if param_name in kwargs and kwargs[param_name] is not None:
            service = kwargs[param_name]
            if _is_rbac_service_like(service):
                return service
    
    # Pattern 2: Check positional arguments for service-like objects
    for arg in args:
        if _is_rbac_service_like(arg):
            return arg
    
    # Pattern 3: Try service registry (includes service stack)
    try:
        service = get_rbac_service()
        if _is_rbac_service_like(service):
            return service
    except ValueError:
        pass
    
    raise ValueError(
        "No RBAC service available. Please either:\n"
        "1. Pass rbac_service as a parameter to your function\n"
        "2. Register a service using set_rbac_service()\n"
        "3. Pass service as positional argument"
    )


def _is_rbac_service_like(obj: Any) -> bool:
    """Check if object looks like an RBAC service.
    
    Args:
        obj: Object to check
        
    Returns:
        True if object has RBAC service methods, False otherwise
    """
    if obj is None:
        return False
        
    # Check for required RBAC service methods
    required_methods = ['check_permission', 'check_resource_ownership']
    
    try:
        for method_name in required_methods:
            if not hasattr(obj, method_name):
                return False
            method = getattr(obj, method_name)
            if not callable(method):
                return False
        return True
    except (AttributeError, TypeError):
        return False


class Permission:
    """Permission definition for resources and actions.

    Represents a specific permission like "document:read" or "project:create".
    Supports context for advanced permission scenarios.
    """

    def __init__(self, resource: str, action: str, context: Optional[dict[str, Any]] = None):
        """Initializes the permission.

        Args:
            resource (str): Resource type (e.g., "document", "project").
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
            resource_type (str): Type of resource (e.g., "document", "project").
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

            # Get RBAC service from context
            try:
                rbac_service = _get_rbac_service_from_context(args, kwargs)
            except ValueError as e:
                logger.error(f"RBAC service injection failed: {e}")
                raise HTTPException(status_code=500, detail="RBAC service not available")

            # Evaluate requirements with OR logic between decorator groups
            for requirement_group in all_requirements:
                try:
                    if await _evaluate_requirement_group(
                        user, requirement_group, original_func, args, kwargs, rbac_service
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
        wrapper._rbac_requirements = all_requirements  # type: ignore
        wrapper._rbac_original_func = original_func  # type: ignore
        return wrapper

    return decorator


async def _evaluate_requirement_group(
        user: UserProtocol, requirements: tuple, func: Callable, args: tuple, kwargs: dict, rbac_service: Any
) -> bool:
    """Evaluate a single requirement group with AND logic."""
    has_role_requirement = False
    has_permission_requirement = False
    has_ownership_requirement = False

    role_satisfied = True
    permission_satisfied = True
    ownership_satisfied = True

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
        if isinstance(role_req, Enum):
            return user.has_role(role_req.value)
        elif isinstance(role_req, RoleComposition):
            return any(user.has_role(role.value) for role in role_req.roles)
        elif isinstance(role_req, list):
            # Handle list of Enums
            for role in role_req:
                if user.has_role(role.value):
                    return True
            return False

    # Fallback to direct attribute access check
    current_role = user.role  # String value

    if isinstance(role_req, Enum):
        return current_role == role_req.value

    elif isinstance(role_req, RoleComposition):
        return any(current_role == role.value for role in role_req.roles)

    elif isinstance(role_req, list):
        # Handle list of Enums
        for role in role_req:
            if current_role == role.value:
                return True
        return False

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
