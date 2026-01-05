"""Ownership provider system for resource access control.

This module provides the protocol and registry for pluggable ownership validation,
allowing users to register custom ownership validators per resource type.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from fastapi_role.protocols.user import UserProtocol


class OwnershipProvider(Protocol):
    """Protocol for custom ownership validators.
    
    Implementations should check if a user owns or has access to a specific resource.
    """

    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check if user owns or has access to the resource.
        
        Args:
            user: The user to check ownership for.
            resource_type: Type of resource (e.g., "order", "project", "customer").
            resource_id: Unique identifier of the resource.
            
        Returns:
            bool: True if user has ownership/access, False otherwise.
        """
        ...


class OwnershipRegistry:
    """Registry for resource ownership providers.
    
    Manages registration and lookup of ownership validators per resource type.
    Provides fallback behavior for unregistered resource types.
    """

    def __init__(self, default_allow: bool = False):
        """Initialize the ownership registry.
        
        Args:
            default_allow: Default behavior for unregistered resource types.
                          If True, allows access. If False, denies access.
        """
        self._providers: Dict[str, OwnershipProvider] = {}
        self._default_allow = default_allow

    def register(self, resource_type: str, provider: OwnershipProvider) -> None:
        """Register an ownership provider for a resource type.
        
        Args:
            resource_type: Type of resource to register provider for.
            provider: The ownership provider implementation.
        """
        self._providers[resource_type] = provider

    async def check(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check ownership using registered provider or default behavior.
        
        Args:
            user: The user to check ownership for.
            resource_type: Type of resource being accessed.
            resource_id: Unique identifier of the resource.
            
        Returns:
            bool: True if user has ownership/access, False otherwise.
        """
        provider = self._providers.get(resource_type)
        
        if provider:
            return await provider.check_ownership(user, resource_type, resource_id)
        
        # No provider registered - use default behavior
        return self._default_allow

    def has_provider(self, resource_type: str) -> bool:
        """Check if a provider is registered for a resource type.
        
        Args:
            resource_type: Type of resource to check.
            
        Returns:
            bool: True if provider is registered, False otherwise.
        """
        return resource_type in self._providers

    def unregister(self, resource_type: str) -> Optional[OwnershipProvider]:
        """Unregister a provider for a resource type.
        
        Args:
            resource_type: Type of resource to unregister.
            
        Returns:
            Optional[OwnershipProvider]: The removed provider, or None if not found.
        """
        return self._providers.pop(resource_type, None)
