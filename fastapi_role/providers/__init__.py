"""Default ownership provider implementations.

This module provides default ownership validation logic including superadmin bypass.
"""

from __future__ import annotations

from typing import Any, Optional, Set

from fastapi_role.protocols import UserProtocol


class DefaultOwnershipProvider:
    """Default ownership provider with superadmin bypass.
    
    Provides a simple ownership validation strategy:
    - Superadmin role always has access (if configured)
    - Otherwise, uses configurable default behavior
    """

    def __init__(
        self,
        superadmin_role: str = "superadmin",
        default_allow: bool = False,
        allowed_roles: Optional[Set[str]] = None,
    ):
        """Initialize the default ownership provider.
        
        Args:
            superadmin_role: Role name that bypasses all ownership checks.
            default_allow: Default behavior when user is not superadmin.
            allowed_roles: Optional set of roles that are always allowed access.
        """
        self.superadmin_role = superadmin_role
        self.default_allow = default_allow
        self.allowed_roles = allowed_roles or set()

    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check ownership with superadmin bypass.
        
        Args:
            user: The user to check ownership for.
            resource_type: Type of resource being accessed.
            resource_id: Unique identifier of the resource.
            
        Returns:
            bool: True if user has ownership/access, False otherwise.
        """
        # Superadmin bypass
        if user.role == self.superadmin_role:
            return True
        
        # Check allowed roles
        if user.role in self.allowed_roles:
            return True
        
        # Default behavior
        return self.default_allow
