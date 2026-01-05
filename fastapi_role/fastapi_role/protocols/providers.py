"""Provider protocols for fastapi-role.

This module defines the provider protocols for pluggable components:
- SubjectProvider: Extract Casbin subject identifier from user
- RoleProvider: Extract and validate user roles
- CacheProvider: Pluggable caching backend
"""

from __future__ import annotations

from typing import Optional, Protocol

from fastapi_role.protocols.user import UserProtocol


class SubjectProvider(Protocol):
    """Protocol for extracting Casbin subject identifier from user.
    
    The subject is used as the first parameter in Casbin policy evaluation.
    Common implementations use email, user ID, or composite identifiers.
    """

    def get_subject(self, user: UserProtocol) -> str:
        """Extract the Casbin subject identifier from user.
        
        Args:
            user: The user object to extract subject from.
            
        Returns:
            str: The subject identifier (e.g., email, user ID).
        """
        ...


class RoleProvider(Protocol):
    """Protocol for extracting and validating user roles.
    
    Provides methods to get user's role and check role membership,
    with support for superadmin bypass and multi-role scenarios.
    """

    def get_role(self, user: UserProtocol) -> str:
        """Get the user's primary role.
        
        Args:
            user: The user object to extract role from.
            
        Returns:
            str: The user's role name.
        """
        ...

    def has_role(self, user: UserProtocol, role_name: str) -> bool:
        """Check if user has the specified role.
        
        Args:
            user: The user object to check.
            role_name: The role name to check for.
            
        Returns:
            bool: True if user has the role, False otherwise.
        """
        ...


class CacheProvider(Protocol):
    """Protocol for pluggable caching backend.
    
    Provides methods for caching permission check results with optional TTL.
    Implementations can use in-memory, Redis, Memcached, or other backends.
    """

    def get(self, key: str) -> Optional[bool]:
        """Get cached value for key.
        
        Args:
            key: The cache key.
            
        Returns:
            Optional[bool]: The cached value, or None if not found or expired.
        """
        ...

    def set(self, key: str, value: bool, ttl: Optional[int] = None) -> None:
        """Set cached value for key.
        
        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Optional time-to-live in seconds.
        """
        ...

    def clear(self) -> None:
        """Clear all cached values."""
        ...

    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            dict: Statistics including size, hits, misses, etc.
        """
        ...
