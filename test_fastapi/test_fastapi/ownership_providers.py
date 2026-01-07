"""
Custom ownership providers for the test application.
Demonstrates resource-specific ownership validation with pure general RBAC.
"""
from typing import Any
from sqlalchemy.orm import Session

from fastapi_role.protocols import UserProtocol
from fastapi_role.core.ownership import OwnershipProvider

from .database import SessionLocal
from .models import Document, Project, Task


class DocumentOwnershipProvider:
    """Ownership provider for Document resources.
    
    Validates that users can only access documents they own,
    with special handling for public documents and admin access.
    """
    
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check if user owns or can access the document."""
        
        # Admin and manager roles have access to all documents
        if user.role in ["admin", "manager"]:
            return True
        
        # Get database session
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == resource_id).first()
            
            if not document:
                return False
            
            # User owns the document
            if document.owner_id == user.id:
                return True
            
            # Document is public (read-only access)
            if document.is_public:
                return True
            
            return False
            
        finally:
            db.close()


class ProjectOwnershipProvider:
    """Ownership provider for Project resources.
    
    Validates project ownership with support for public projects
    and hierarchical access control.
    """
    
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check if user owns or can access the project."""
        
        # Admin and manager roles have access to all projects
        if user.role in ["admin", "manager"]:
            return True
        
        # Get database session
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == resource_id).first()
            
            if not project:
                return False
            
            # User owns the project
            if project.owner_id == user.id:
                return True
            
            # Project is public (read-only access for most operations)
            if project.is_public:
                return True
            
            return False
            
        finally:
            db.close()


class TaskOwnershipProvider:
    """Ownership provider for Task resources.
    
    Validates task ownership based on assignee, with support for
    project-based access and hierarchical permissions.
    """
    
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check if user owns or can access the task."""
        
        # Admin and manager roles have access to all tasks
        if user.role in ["admin", "manager"]:
            return True
        
        # Get database session
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == resource_id).first()
            
            if not task:
                return False
            
            # User is assigned to the task
            if task.assignee_id == user.id:
                return True
            
            # If task belongs to a project, check project ownership
            if task.project_id:
                project = db.query(Project).filter(Project.id == task.project_id).first()
                if project:
                    # Project owner can manage tasks in their project
                    if project.owner_id == user.id:
                        return True
                    
                    # Tasks in public projects are visible (but not necessarily editable)
                    if project.is_public:
                        return True
            
            return False
            
        finally:
            db.close()


class UserOwnershipProvider:
    """Ownership provider for User resources.
    
    Validates user access with self-service capabilities
    and administrative overrides.
    """
    
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check if user can access the user resource."""
        
        # Admin role has access to all users
        if user.role == "admin":
            return True
        
        # Users can access their own profile
        if user.id == resource_id:
            return True
        
        # Manager role can read (but not modify) other users
        # This would be handled at the permission level, not ownership
        return False


class SuperAdminOwnershipProvider:
    """Special ownership provider that grants access to superadmin users.
    
    This can be used as a fallback or wrapper around other providers
    to ensure superadmin users always have access.
    """
    
    def __init__(self, wrapped_provider: OwnershipProvider, superadmin_role: str = "admin"):
        """Initialize with wrapped provider and superadmin role.
        
        Args:
            wrapped_provider: The provider to wrap with superadmin bypass.
            superadmin_role: Role name that gets superadmin access.
        """
        self.wrapped_provider = wrapped_provider
        self.superadmin_role = superadmin_role
    
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check ownership with superadmin bypass."""
        
        # Superadmin bypass
        if user.role == self.superadmin_role:
            return True
        
        # Delegate to wrapped provider
        return await self.wrapped_provider.check_ownership(user, resource_type, resource_id)


class CompositeOwnershipProvider:
    """Composite ownership provider that combines multiple providers.
    
    Useful for resources that have multiple ownership patterns
    or complex access rules.
    """
    
    def __init__(self, providers: list[OwnershipProvider], require_all: bool = False):
        """Initialize with list of providers.
        
        Args:
            providers: List of ownership providers to check.
            require_all: If True, all providers must grant access.
                        If False, any provider granting access is sufficient.
        """
        self.providers = providers
        self.require_all = require_all
    
    async def check_ownership(
        self, user: UserProtocol, resource_type: str, resource_id: Any
    ) -> bool:
        """Check ownership using composite logic."""
        
        if not self.providers:
            return False
        
        results = []
        for provider in self.providers:
            result = await provider.check_ownership(user, resource_type, resource_id)
            results.append(result)
            
            # Short-circuit optimization
            if self.require_all and not result:
                return False
            elif not self.require_all and result:
                return True
        
        # Return based on mode
        return all(results) if self.require_all else any(results)


# Factory function to create all providers
def create_ownership_providers() -> dict[str, OwnershipProvider]:
    """Create and return all ownership providers for the test application.
    
    Returns:
        dict: Mapping of resource types to ownership providers.
    """
    return {
        "document": DocumentOwnershipProvider(),
        "project": ProjectOwnershipProvider(), 
        "task": TaskOwnershipProvider(),
        "user": UserOwnershipProvider(),
    }


# Factory function to create providers with superadmin bypass
def create_ownership_providers_with_superadmin(superadmin_role: str = "admin") -> dict[str, OwnershipProvider]:
    """Create ownership providers with superadmin bypass.
    
    Args:
        superadmin_role: Role name that gets superadmin access.
        
    Returns:
        dict: Mapping of resource types to ownership providers with superadmin bypass.
    """
    base_providers = create_ownership_providers()
    
    return {
        resource_type: SuperAdminOwnershipProvider(provider, superadmin_role)
        for resource_type, provider in base_providers.items()
    }