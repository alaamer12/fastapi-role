"""
RBAC setup for the generic test application.
Demonstrates pure general RBAC with dynamic roles and resource-agnostic policies.
"""
from typing import Any, Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from fastapi_role.core.roles import create_roles
from fastapi_role.core.config import CasbinConfig, Policy
from fastapi_role.rbac_service import RBACService
from fastapi_role.protocols import UserProtocol
from fastapi_role.providers import DefaultSubjectProvider, DefaultRoleProvider

from .database import get_db, SessionLocal
from .config import settings, get_rbac_model_text, get_rbac_policies
from .models import User
from .ownership_providers import create_ownership_providers_with_superadmin


# Create dynamic roles from configuration
Role = create_roles(settings.rbac_roles)


class TestAppSubjectProvider(DefaultSubjectProvider):
    """Subject provider that uses user email as subject"""
    
    def get_subject(self, user: UserProtocol) -> str:
        return user.email


class TestAppRoleProvider(DefaultRoleProvider):
    """Role provider with superadmin bypass"""
    
    def __init__(self):
        super().__init__(superadmin_role=settings.rbac_superadmin_role)
    
    def get_role(self, user: UserProtocol) -> str:
        """Get the user's primary role"""
        return user.role
    
    async def get_user_roles(self, user: UserProtocol) -> list[str]:
        """Get user roles - in this case, just the single role"""
        return [user.role]
    
    def has_role(self, user: UserProtocol, role_name: str) -> bool:
        """Check if user has specific role"""
        # Check direct role match
        if user.role == role_name:
            return True
        
        # Check superadmin bypass
        if self.superadmin_role and user.role == self.superadmin_role:
            return True
            
        return False


def create_rbac_config() -> CasbinConfig:
    """Create RBAC configuration with dynamic policies"""
    
    # Create configuration with custom model
    config = CasbinConfig(
        app_name="test-fastapi-rbac",
        superadmin_role=settings.rbac_superadmin_role,
        model_content=get_rbac_model_text()
    )
    
    # Add policies from configuration
    policies = get_rbac_policies()
    for policy in policies:
        if len(policy) >= 3:
            subject, obj, act = policy[0], policy[1], policy[2]
            # Use the Policy class to create policy objects
            config.policies.append(Policy(subject, obj, act))
    
    # Add role assignments (grouping policies) - users inherit from their roles
    # This is needed so that when we check permissions for a user with role "admin",
    # Casbin knows that user inherits the "admin" role permissions
    # Note: In our case, the subject provider returns email and role provider returns role,
    # so we need to map user emails to their roles
    
    return config


def create_rbac_service() -> RBACService:
    """Create and configure RBAC service"""
    
    config = create_rbac_config()
    
    # Create providers
    subject_provider = TestAppSubjectProvider()
    role_provider = TestAppRoleProvider()
    
    # Create RBAC service
    rbac_service = RBACService(
        config=config,
        subject_provider=subject_provider,
        role_provider=role_provider
    )
    
    # Add grouping policies to map users to their roles
    # This is needed because Casbin needs to know which users have which roles
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            # Add grouping policy: user email -> user role
            rbac_service.enforcer.add_grouping_policy(user.email, user.role)
    finally:
        db.close()
    
    # Register custom ownership providers after service creation
    ownership_providers = create_ownership_providers_with_superadmin(settings.rbac_superadmin_role)
    
    for resource_type, provider in ownership_providers.items():
        rbac_service.ownership_registry.register(resource_type, provider)
    
    return rbac_service


# Global RBAC service instance
_rbac_service: Optional[RBACService] = None


def get_rbac_service() -> RBACService:
    """Dependency to get RBAC service"""
    global _rbac_service
    
    if _rbac_service is None:
        _rbac_service = create_rbac_service()
    
    return _rbac_service


# Convenience function for checking permissions
async def check_permission(
    user: User,
    resource_type: str,
    action: str,
    rbac: RBACService = Depends(get_rbac_service)
) -> bool:
    """Check if user has permission for resource action"""
    return await rbac.check_permission(user, resource_type, action)


# Convenience function for checking ownership
async def check_ownership(
    user: User,
    resource_type: str,
    resource_id: Any,
    rbac: RBACService = Depends(get_rbac_service)
) -> bool:
    """Check if user owns the resource"""
    from fastapi_role.core.resource import ResourceRef
    resource = ResourceRef(resource_type, resource_id)
    return await rbac.check_ownership(user, resource)