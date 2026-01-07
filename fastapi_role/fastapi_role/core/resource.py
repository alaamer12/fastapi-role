"""Generic resource reference system for RBAC.

This module provides resource-agnostic data structures for the RBAC system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ResourceRef:
    """Generic resource reference - works with any domain.
    
    This class represents any resource in the system without making assumptions
    about what the resource represents (order, project, document, etc.).
    """
    
    type: str  # Generic resource type: "order", "project", "document", "user", etc.
    id: Any    # Resource ID: int, UUID, str, composite key, etc.
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
    
    def __str__(self) -> str:
        """String representation of resource reference."""
        return f"{self.type}:{self.id}"
        
    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash((self.type, str(self.id)))
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, ResourceRef):
            return False
        return self.type == other.type and self.id == other.id


@dataclass 
class Permission:
    """Generic permission - no business assumptions.
    
    Represents a permission for a specific resource type and action.
    """
    
    resource: str  # Generic resource type
    action: str    # Generic action
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize context if not provided."""
        if self.context is None:
            self.context = {}
    
    def __str__(self) -> str:
        """String representation of permission."""
        return f"{self.resource}:{self.action}"
    
    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash((self.resource, self.action))
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, Permission):
            return False
        return self.resource == other.resource and self.action == other.action


@dataclass
class Privilege:
    """Generic privilege bundle.
    
    Combines roles, permissions, and ownership requirements into a reusable
    authorization specification.
    """
    
    name: str
    roles: Optional[list[str]] = None
    permissions: Optional[list[Permission]] = None
    ownership_required: Optional[list[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize optional fields if not provided."""
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.ownership_required is None:
            self.ownership_required = []
        if self.conditions is None:
            self.conditions = {}
    
    def __str__(self) -> str:
        """String representation of privilege."""
        return f"Privilege({self.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Privilege(name='{self.name}', roles={self.roles}, "
            f"permissions={self.permissions}, ownership_required={self.ownership_required})"
        )