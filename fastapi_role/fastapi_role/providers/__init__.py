"""Default provider implementations for fastapi-role.

This module provides default implementations for all provider protocols:
- DefaultOwnershipProvider: Ownership validation with superadmin bypass
- DefaultSubjectProvider: Extract Casbin subject from user
- DefaultRoleProvider: Extract and validate user roles
- DefaultCacheProvider: In-memory caching backend
"""

from __future__ import annotations

from datetime import datetime, timedelta
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
        superadmin_role: Optional[str] = None,
        default_allow: bool = False,
        allowed_roles: Optional[Set[str]] = None,
    ):
        """Initialize the default ownership provider.
        
        Args:
            superadmin_role: Role name that bypasses all ownership checks. If None, no superadmin bypass.
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
        # Superadmin bypass (only if superadmin_role is configured)
        if self.superadmin_role and user.role == self.superadmin_role:
            return True
        
        # Check allowed roles
        if user.role in self.allowed_roles:
            return True
        
        # Default behavior
        return self.default_allow


class DefaultSubjectProvider:
    """Default subject provider using user email.
    
    Extracts the Casbin subject identifier from user object.
    By default uses email, but can be configured to use other fields.
    """

    def __init__(self, field_name: str = "email"):
        """Initialize the default subject provider.
        
        Args:
            field_name: Name of the user attribute to use as subject.
        """
        self.field_name = field_name

    def get_subject(self, user: UserProtocol) -> str:
        """Extract the Casbin subject identifier from user.
        
        Args:
            user: The user object to extract subject from.
            
        Returns:
            str: The subject identifier (e.g., email, user ID).
        """
        return str(getattr(user, self.field_name))


class DefaultRoleProvider:
    """Default role provider using user role attribute.
    
    Extracts and validates user roles with optional superadmin bypass.
    """

    def __init__(self, superadmin_role: Optional[str] = None):
        """Initialize the default role provider.
        
        Args:
            superadmin_role: Role name that has all permissions. If None, no superadmin bypass.
        """
        self.superadmin_role = superadmin_role

    def get_role(self, user: UserProtocol) -> str:
        """Get the user's primary role.
        
        Args:
            user: The user object to extract role from.
            
        Returns:
            str: The user's role name.
        """
        return user.role

    def has_role(self, user: UserProtocol, role_name: str) -> bool:
        """Check if user has the specified role.
        
        Superadmin role always returns True for any role check (if configured).
        
        Args:
            user: The user object to check.
            role_name: The role name to check for.
            
        Returns:
            bool: True if user has the role, False otherwise.
        """
        # Superadmin bypass (only if superadmin_role is configured)
        if self.superadmin_role and user.role == self.superadmin_role:
            return True
        
        # Direct role comparison
        return user.role == role_name


class DefaultCacheProvider:
    """Default in-memory cache provider.
    
    Provides simple dictionary-based caching with optional TTL support.
    """

    def __init__(self, default_ttl: Optional[int] = None):
        """Initialize the default cache provider.
        
        Args:
            default_ttl: Default time-to-live in seconds for cached values.
        """
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[bool, Optional[datetime]]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[bool]:
        """Get cached value for key.
        
        Args:
            key: The cache key.
            
        Returns:
            Optional[bool]: The cached value, or None if not found or expired.
        """
        if key not in self._cache:
            self._misses += 1
            return None
        
        value, expiry = self._cache[key]
        
        # Check if expired
        if expiry is not None and datetime.utcnow() > expiry:
            del self._cache[key]
            self._misses += 1
            return None
        
        self._hits += 1
        return value

    def set(self, key: str, value: bool, ttl: Optional[int] = None) -> None:
        """Set cached value for key.
        
        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Optional time-to-live in seconds (overrides default_ttl).
        """
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        expiry = None
        
        if ttl_seconds is not None:
            expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        self._cache[key] = (value, expiry)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            dict: Statistics including size, hits, misses.
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }
