#!/usr/bin/env python3
"""
Minimal Pure RBAC Example - Single File FastAPI Application

This example demonstrates the pure general RBAC system with:
- No business assumptions or hardcoded concepts
- Generic resource types and dynamic roles
- In-memory configuration (no external files)
- Basic protected endpoints

Run with: python examples/minimal_rbac_example.py
Then visit: http://localhost:8000/docs
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

# Import the pure general RBAC system
from fastapi_role import (
    create_roles,
    CasbinConfig,
    RBACService,
    require,
    set_rbac_service,
    ResourceRef,
    Permission as CorePermission,
)
from fastapi_role.core.config import Policy
from fastapi_role.protocols import UserProtocol
from fastapi_role.providers import DefaultSubjectProvider, DefaultRoleProvider


# ============================================================================
# Configuration - No Business Assumptions
# ============================================================================

# Dynamic role creation - completely configurable
ROLE_NAMES = ["admin", "manager", "user"]
SUPERADMIN_ROLE = "admin"

# Generic resource types - works with any domain
RESOURCE_TYPES = ["document", "project", "task"]

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ============================================================================
# Data Models - Generic, No Business Coupling
# ============================================================================

class UserModel(BaseModel):
    """Generic user model implementing UserProtocol"""
    id: int
    email: str
    role: str
    name: str
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role"""
        return self.role == role_name


@dataclass
class GenericResource:
    """Generic resource - works with any resource type"""
    id: int
    type: str
    title: str
    owner_id: int
    is_public: bool = False
    
    def to_resource_ref(self) -> ResourceRef:
        """Convert to ResourceRef for RBAC operations"""
        return ResourceRef(self.type, self.id)


class TokenData(BaseModel):
    """Token payload"""
    email: str
    role: str


class LoginRequest(BaseModel):
    """Login request"""
    email: str
    password: str


class ResourceResponse(BaseModel):
    """Generic resource response"""
    id: int
    type: str
    title: str
    owner_id: int
    is_public: bool
    can_edit: bool = False
    can_delete: bool = False


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# ============================================================================
# In-Memory Data Store - No Database Dependencies
# ============================================================================

# Sample users - completely generic
USERS: Dict[str, UserModel] = {
    "admin@example.com": UserModel(id=1, email="admin@example.com", role="admin", name="Admin User"),
    "manager@example.com": UserModel(id=2, email="manager@example.com", role="manager", name="Manager User"),
    "user@example.com": UserModel(id=3, email="user@example.com", role="user", name="Regular User"),
}

# Sample resources - generic, no business assumptions
RESOURCES: List[GenericResource] = [
    GenericResource(1, "document", "Public Document", 1, True),
    GenericResource(2, "document", "Admin Document", 1, False),
    GenericResource(3, "project", "Public Project", 2, True),
    GenericResource(4, "project", "Manager Project", 2, False),
    GenericResource(5, "task", "User Task", 3, False),
]


# ============================================================================
# RBAC Configuration - Pure General, No Business Logic
# ============================================================================

def create_rbac_config() -> CasbinConfig:
    """Create pure general RBAC configuration"""
    
    # Create configuration with default RBAC model
    config = CasbinConfig(
        app_name="minimal-rbac-example",
        superadmin_role=SUPERADMIN_ROLE
    )
    
    # Add generic policies - no business assumptions
    policies = [
        # Admin can do everything
        ("admin", "*", "*"),
        
        # Manager can read all, write own resources
        ("manager", "*", "read"),
        ("manager", "document", "create"),
        ("manager", "project", "create"),
        ("manager", "task", "create"),
        
        # User can read public resources, manage own resources
        ("user", "*", "read"),  # Will be filtered by ownership/public status
        ("user", "task", "create"),
    ]
    
    for subject, obj, act in policies:
        config.add_policy(subject, obj, act)
    
    return config


class MinimalOwnershipProvider:
    """Minimal ownership provider for the example"""
    
    def __init__(self, superadmin_role: Optional[str] = None):
        self.superadmin_role = superadmin_role
    
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        """Check if user owns the resource or has access"""
        
        # Superadmin bypass
        if self.superadmin_role and user.role == self.superadmin_role:
            return True
        
        # Find the resource
        resource = next((r for r in RESOURCES if r.id == resource_id and r.type == resource_type), None)
        if not resource:
            return False
        
        # Owner always has access
        if resource.owner_id == user.id:
            return True
        
        # Public resources are readable by anyone
        if resource.is_public:
            return True
        
        return False


def setup_rbac() -> RBACService:
    """Setup the pure general RBAC system"""
    
    # Create dynamic roles
    Role = create_roles(ROLE_NAMES)
    
    # Create RBAC configuration
    config = create_rbac_config()
    
    # Create providers
    subject_provider = DefaultSubjectProvider(field_name="email")
    role_provider = DefaultRoleProvider(superadmin_role=SUPERADMIN_ROLE)
    
    # Create RBAC service
    rbac_service = RBACService(
        config=config,
        subject_provider=subject_provider,
        role_provider=role_provider
    )
    
    # Add user-role mappings to Casbin
    for user in USERS.values():
        rbac_service.enforcer.add_grouping_policy(user.email, user.role)
    
    # Register ownership provider for all resource types
    ownership_provider = MinimalOwnershipProvider(superadmin_role=SUPERADMIN_ROLE)
    for resource_type in RESOURCE_TYPES:
        rbac_service.ownership_registry.register(resource_type, ownership_provider)
    
    return rbac_service


# ============================================================================
# Authentication - Simple JWT Implementation
# ============================================================================

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserModel:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = USERS.get(email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================================
# FastAPI Application - Framework-Agnostic RBAC
# ============================================================================

app = FastAPI(
    title="Minimal Pure RBAC Example",
    description="Demonstrates pure general RBAC with no business assumptions",
    version="1.0.0"
)

# Setup RBAC system
rbac_service = setup_rbac()
set_rbac_service(rbac_service)


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/login")
async def login(request: LoginRequest):
    """Login endpoint - simplified for demo"""
    # In real app, verify password hash
    user = USERS.get(request.email)
    if not user or request.password != "password":  # Simplified for demo
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@app.get("/me")
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# ============================================================================
# Protected Endpoints - Pure General RBAC
# ============================================================================

@app.get("/", response_model=MessageResponse)
async def root():
    """Root endpoint"""
    return MessageResponse(message="Minimal Pure RBAC Example - No Business Assumptions")


@app.get("/resources", response_model=List[ResourceResponse])
@require(CorePermission("*", "read"))
async def list_resources(
    resource_type: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """List resources with access control"""
    
    # Filter by resource type if specified
    resources = RESOURCES
    if resource_type:
        resources = [r for r in resources if r.type == resource_type]
    
    # Check access for each resource
    accessible_resources = []
    for resource in resources:
        # Check if user can access this resource
        can_access = await rbac.can_access(
            current_user, 
            resource.to_resource_ref(), 
            "read"
        )
        
        if can_access:
            # Check additional permissions
            can_edit = await rbac.can_access(current_user, resource.to_resource_ref(), "update")
            can_delete = await rbac.can_access(current_user, resource.to_resource_ref(), "delete")
            
            accessible_resources.append(ResourceResponse(
                id=resource.id,
                type=resource.type,
                title=resource.title,
                owner_id=resource.owner_id,
                is_public=resource.is_public,
                can_edit=can_edit,
                can_delete=can_delete
            ))
    
    return accessible_resources


@app.get("/resources/{resource_type}/{resource_id}", response_model=ResourceResponse)
@require(CorePermission("*", "read"))
async def get_resource(
    resource_type: str,
    resource_id: int,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Get specific resource with access control"""
    
    # Find resource
    resource = next((r for r in RESOURCES if r.id == resource_id and r.type == resource_type), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Check access
    can_access = await rbac.can_access(current_user, resource.to_resource_ref(), "read")
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check additional permissions
    can_edit = await rbac.can_access(current_user, resource.to_resource_ref(), "update")
    can_delete = await rbac.can_access(current_user, resource.to_resource_ref(), "delete")
    
    return ResourceResponse(
        id=resource.id,
        type=resource.type,
        title=resource.title,
        owner_id=resource.owner_id,
        is_public=resource.is_public,
        can_edit=can_edit,
        can_delete=can_delete
    )


@app.post("/resources/{resource_type}", response_model=ResourceResponse)
@require(CorePermission("*", "create"))
async def create_resource(
    resource_type: str,
    title: str,
    is_public: bool = False,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Create new resource with access control"""
    
    # Check if user can create this resource type
    can_create = await rbac.check_permission(current_user, resource_type, "create")
    if not can_create:
        raise HTTPException(status_code=403, detail=f"Cannot create {resource_type}")
    
    # Create new resource
    new_id = max([r.id for r in RESOURCES], default=0) + 1
    new_resource = GenericResource(
        id=new_id,
        type=resource_type,
        title=title,
        owner_id=current_user.id,
        is_public=is_public
    )
    
    RESOURCES.append(new_resource)
    
    return ResourceResponse(
        id=new_resource.id,
        type=new_resource.type,
        title=new_resource.title,
        owner_id=new_resource.owner_id,
        is_public=new_resource.is_public,
        can_edit=True,  # Owner can always edit
        can_delete=True  # Owner can always delete
    )


@app.put("/resources/{resource_type}/{resource_id}", response_model=ResourceResponse)
@require(CorePermission("*", "update"))
async def update_resource(
    resource_type: str,
    resource_id: int,
    title: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Update resource with access control"""
    
    # Find resource
    resource = next((r for r in RESOURCES if r.id == resource_id and r.type == resource_type), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Check access
    can_update = await rbac.can_access(current_user, resource.to_resource_ref(), "update")
    if not can_update:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update resource
    if title is not None:
        resource.title = title
    if is_public is not None:
        resource.is_public = is_public
    
    return ResourceResponse(
        id=resource.id,
        type=resource.type,
        title=resource.title,
        owner_id=resource.owner_id,
        is_public=resource.is_public,
        can_edit=True,
        can_delete=await rbac.can_access(current_user, resource.to_resource_ref(), "delete")
    )


@app.delete("/resources/{resource_type}/{resource_id}", response_model=MessageResponse)
@require(CorePermission("*", "delete"))
async def delete_resource(
    resource_type: str,
    resource_id: int,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Delete resource with access control"""
    
    # Find resource
    resource = next((r for r in RESOURCES if r.id == resource_id and r.type == resource_type), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Check access
    can_delete = await rbac.can_access(current_user, resource.to_resource_ref(), "delete")
    if not can_delete:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete resource
    RESOURCES.remove(resource)
    
    return MessageResponse(message=f"Resource {resource_type}:{resource_id} deleted successfully")


# ============================================================================
# Admin Endpoints - Demonstrate Role-Based Access
# ============================================================================

@app.get("/admin/users", response_model=List[UserModel])
@require(CorePermission("user", "read"))
async def list_users(
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """List all users - admin only"""
    
    # Additional role check for admin operations
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return list(USERS.values())


@app.get("/admin/stats", response_model=Dict[str, Any])
@require(CorePermission("system", "read"))
async def get_system_stats(
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Get system statistics - admin only"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Count resources by type
    resource_counts = {}
    for resource_type in RESOURCE_TYPES:
        resource_counts[resource_type] = len([r for r in RESOURCES if r.type == resource_type])
    
    return {
        "total_users": len(USERS),
        "total_resources": len(RESOURCES),
        "resource_counts": resource_counts,
        "cache_stats": rbac.get_cache_stats()
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Minimal Pure RBAC Example")
    print("=" * 60)
    print("This example demonstrates:")
    print("- Pure general RBAC with no business assumptions")
    print("- Dynamic role creation")
    print("- Generic resource types")
    print("- In-memory configuration")
    print("- Framework-agnostic decorators")
    print()
    print("Test users:")
    for email, user in USERS.items():
        print(f"  {email} (role: {user.role}, password: password)")
    print()
    print("Starting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        "minimal_rbac_example:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )