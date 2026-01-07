#!/usr/bin/env python3
"""
File-Based Configuration RBAC Example

This example demonstrates the pure general RBAC system with:
- Configuration-driven role and policy definition
- Multiple generic resource types
- Custom ownership providers
- File-based policy storage
- YAML configuration files

Run with: python examples/file_based_rbac_example.py
Then visit: http://localhost:8000/docs
"""

import os
import yaml
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, Query
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
)
from fastapi_role.rbac import Permission
from fastapi_role.protocols import UserProtocol
from fastapi_role.providers import DefaultSubjectProvider, DefaultRoleProvider


# ============================================================================
# Configuration Directory Setup
# ============================================================================

CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)

ROLES_CONFIG_FILE = CONFIG_DIR / "roles.yaml"
POLICIES_CONFIG_FILE = CONFIG_DIR / "policies.yaml"
RESOURCES_CONFIG_FILE = CONFIG_DIR / "resources.yaml"
USERS_CONFIG_FILE = CONFIG_DIR / "users.yaml"


# ============================================================================
# Configuration Models
# ============================================================================

@dataclass
class RoleConfig:
    """Role configuration from YAML"""
    name: str
    description: str
    permissions: List[str]
    inherits_from: Optional[List[str]] = None


@dataclass
class PolicyConfig:
    """Policy configuration from YAML"""
    subject: str  # role or user
    object: str   # resource type or specific resource
    action: str   # action name
    effect: str = "allow"  # allow or deny
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class ResourceTypeConfig:
    """Resource type configuration from YAML"""
    name: str
    description: str
    actions: List[str]
    ownership_provider: Optional[str] = None
    default_permissions: Optional[Dict[str, List[str]]] = None


@dataclass
class UserConfig:
    """User configuration from YAML"""
    id: int
    email: str
    name: str
    role: str
    password_hash: str  # In real app, use proper hashing
    attributes: Optional[Dict[str, Any]] = None


# ============================================================================
# Configuration File Templates
# ============================================================================

DEFAULT_ROLES_CONFIG = {
    "roles": [
        {
            "name": "admin",
            "description": "System administrator with full access",
            "permissions": ["*:*"]
        },
        {
            "name": "manager",
            "description": "Manager with read access to all, write access to managed resources",
            "permissions": [
                "*:read",
                "document:create",
                "document:update",
                "project:create",
                "project:update",
                "task:create"
            ]
        },
        {
            "name": "editor",
            "description": "Content editor with document and task management",
            "permissions": [
                "document:read",
                "document:create",
                "document:update",
                "task:read",
                "task:create",
                "task:update"
            ]
        },
        {
            "name": "viewer",
            "description": "Read-only access to public resources",
            "permissions": [
                "document:read",
                "project:read",
                "task:read"
            ]
        }
    ],
    "superadmin_role": "admin"
}

DEFAULT_POLICIES_CONFIG = {
    "policies": [
        # Admin policies
        {"subject": "admin", "object": "*", "action": "*", "effect": "allow"},
        
        # Manager policies
        {"subject": "manager", "object": "*", "action": "read", "effect": "allow"},
        {"subject": "manager", "object": "document", "action": "create", "effect": "allow"},
        {"subject": "manager", "object": "document", "action": "update", "effect": "allow"},
        {"subject": "manager", "object": "project", "action": "create", "effect": "allow"},
        {"subject": "manager", "object": "project", "action": "update", "effect": "allow"},
        {"subject": "manager", "object": "task", "action": "create", "effect": "allow"},
        
        # Editor policies
        {"subject": "editor", "object": "document", "action": "read", "effect": "allow"},
        {"subject": "editor", "object": "document", "action": "create", "effect": "allow"},
        {"subject": "editor", "object": "document", "action": "update", "effect": "allow"},
        {"subject": "editor", "object": "task", "action": "read", "effect": "allow"},
        {"subject": "editor", "object": "task", "action": "create", "effect": "allow"},
        {"subject": "editor", "object": "task", "action": "update", "effect": "allow"},
        
        # Viewer policies
        {"subject": "viewer", "object": "document", "action": "read", "effect": "allow"},
        {"subject": "viewer", "object": "project", "action": "read", "effect": "allow"},
        {"subject": "viewer", "object": "task", "action": "read", "effect": "allow"},
    ]
}

DEFAULT_RESOURCES_CONFIG = {
    "resource_types": [
        {
            "name": "document",
            "description": "Text documents and files",
            "actions": ["read", "create", "update", "delete", "share"],
            "ownership_provider": "document_ownership",
            "default_permissions": {
                "owner": ["read", "update", "delete", "share"],
                "public": ["read"]
            }
        },
        {
            "name": "project",
            "description": "Projects and workspaces",
            "actions": ["read", "create", "update", "delete", "manage_members"],
            "ownership_provider": "project_ownership",
            "default_permissions": {
                "owner": ["read", "update", "delete", "manage_members"],
                "member": ["read", "update"],
                "public": ["read"]
            }
        },
        {
            "name": "task",
            "description": "Tasks and assignments",
            "actions": ["read", "create", "update", "delete", "assign"],
            "ownership_provider": "task_ownership",
            "default_permissions": {
                "owner": ["read", "update", "delete"],
                "assignee": ["read", "update"],
                "public": []
            }
        }
    ]
}

DEFAULT_USERS_CONFIG = {
    "users": [
        {
            "id": 1,
            "email": "admin@example.com",
            "name": "System Administrator",
            "role": "admin",
            "password_hash": "admin_password_hash",
            "attributes": {"department": "IT", "level": "senior"}
        },
        {
            "id": 2,
            "email": "manager@example.com",
            "name": "Project Manager",
            "role": "manager",
            "password_hash": "manager_password_hash",
            "attributes": {"department": "Operations", "level": "senior"}
        },
        {
            "id": 3,
            "email": "editor@example.com",
            "name": "Content Editor",
            "role": "editor",
            "password_hash": "editor_password_hash",
            "attributes": {"department": "Content", "level": "mid"}
        },
        {
            "id": 4,
            "email": "viewer@example.com",
            "name": "Content Viewer",
            "role": "viewer",
            "password_hash": "viewer_password_hash",
            "attributes": {"department": "Marketing", "level": "junior"}
        }
    ]
}


# ============================================================================
# Configuration Manager
# ============================================================================

class ConfigurationManager:
    """Manages file-based configuration loading and saving"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_dir.mkdir(exist_ok=True)
        
    def ensure_config_files(self):
        """Create default configuration files if they don't exist"""
        configs = [
            (ROLES_CONFIG_FILE, DEFAULT_ROLES_CONFIG),
            (POLICIES_CONFIG_FILE, DEFAULT_POLICIES_CONFIG),
            (RESOURCES_CONFIG_FILE, DEFAULT_RESOURCES_CONFIG),
            (USERS_CONFIG_FILE, DEFAULT_USERS_CONFIG),
        ]
        
        for config_file, default_config in configs:
            if not config_file.exists():
                with open(config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False, indent=2)
                print(f"Created default config: {config_file}")
    
    def load_roles_config(self) -> Dict[str, Any]:
        """Load roles configuration from YAML"""
        with open(ROLES_CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    
    def load_policies_config(self) -> Dict[str, Any]:
        """Load policies configuration from YAML"""
        with open(POLICIES_CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    
    def load_resources_config(self) -> Dict[str, Any]:
        """Load resources configuration from YAML"""
        with open(RESOURCES_CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    
    def load_users_config(self) -> Dict[str, Any]:
        """Load users configuration from YAML"""
        with open(USERS_CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    
    def save_policies_config(self, policies_config: Dict[str, Any]):
        """Save policies configuration to YAML"""
        with open(POLICIES_CONFIG_FILE, 'w') as f:
            yaml.dump(policies_config, f, default_flow_style=False, indent=2)


# ============================================================================
# Data Models - Generic, No Business Coupling
# ============================================================================

class UserModel(BaseModel):
    """Generic user model implementing UserProtocol"""
    id: int
    email: str
    role: str
    name: str
    attributes: Optional[Dict[str, Any]] = None
    
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
    metadata: Optional[Dict[str, Any]] = None
    members: Optional[List[int]] = None  # For resources with membership
    assignees: Optional[List[int]] = None  # For resources with assignments
    
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
    metadata: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, bool]] = None


class ResourceCreateRequest(BaseModel):
    """Resource creation request"""
    title: str
    is_public: bool = False
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class ConfigResponse(BaseModel):
    """Configuration response"""
    roles: List[Dict[str, Any]]
    policies: List[Dict[str, Any]]
    resource_types: List[Dict[str, Any]]


# ============================================================================
# Custom Ownership Providers
# ============================================================================

class DocumentOwnershipProvider:
    """Custom ownership provider for documents"""
    
    def __init__(self, superadmin_role: Optional[str] = None):
        self.superadmin_role = superadmin_role
    
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        """Check document ownership with custom logic"""
        
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
        
        # Public documents are readable by anyone
        if resource.is_public:
            return True
        
        # Managers can access all documents
        if user.role == "manager":
            return True
        
        return False


class ProjectOwnershipProvider:
    """Custom ownership provider for projects with membership"""
    
    def __init__(self, superadmin_role: Optional[str] = None):
        self.superadmin_role = superadmin_role
    
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        """Check project ownership with membership logic"""
        
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
        
        # Check project membership
        if resource.members and user.id in resource.members:
            return True
        
        # Public projects are readable by anyone
        if resource.is_public:
            return True
        
        # Managers can access all projects
        if user.role == "manager":
            return True
        
        return False


class TaskOwnershipProvider:
    """Custom ownership provider for tasks with assignment logic"""
    
    def __init__(self, superadmin_role: Optional[str] = None):
        self.superadmin_role = superadmin_role
    
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        """Check task ownership with assignment logic"""
        
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
        
        # Check task assignment
        if resource.assignees and user.id in resource.assignees:
            return True
        
        # Managers and editors can access all tasks
        if user.role in ["manager", "editor"]:
            return True
        
        return False


# ============================================================================
# In-Memory Data Store - Loaded from Configuration
# ============================================================================

# Initialize configuration manager
config_manager = ConfigurationManager(CONFIG_DIR)
config_manager.ensure_config_files()

# Load configuration
users_config = config_manager.load_users_config()
resources_config = config_manager.load_resources_config()

# Create users from configuration
USERS: Dict[str, UserModel] = {}
for user_data in users_config["users"]:
    user = UserModel(**user_data)
    USERS[user.email] = user

# Sample resources - loaded from configuration structure
RESOURCES: List[GenericResource] = [
    # Documents
    GenericResource(1, "document", "Public API Documentation", 1, True, 
                   {"category": "technical", "version": "1.0"}),
    GenericResource(2, "document", "Internal Design Document", 1, False,
                   {"category": "design", "confidential": True}),
    GenericResource(3, "document", "User Manual", 3, True,
                   {"category": "user-guide", "version": "2.1"}),
    
    # Projects
    GenericResource(4, "project", "Website Redesign", 2, False,
                   {"status": "active", "deadline": "2024-03-01"},
                   members=[2, 3]),
    GenericResource(5, "project", "Open Source Library", 1, True,
                   {"status": "active", "license": "MIT"},
                   members=[1, 2, 3, 4]),
    
    # Tasks
    GenericResource(6, "task", "Update Documentation", 2, False,
                   {"priority": "high", "estimated_hours": 8},
                   assignees=[3]),
    GenericResource(7, "task", "Code Review", 1, False,
                   {"priority": "medium", "estimated_hours": 4},
                   assignees=[2, 3]),
    GenericResource(8, "task", "Bug Fix #123", 3, False,
                   {"priority": "urgent", "estimated_hours": 2},
                   assignees=[3]),
]


# ============================================================================
# RBAC Configuration - File-Based
# ============================================================================

def create_rbac_config() -> CasbinConfig:
    """Create RBAC configuration from files"""
    
    # Load configuration
    roles_config = config_manager.load_roles_config()
    policies_config = config_manager.load_policies_config()
    
    # Create configuration
    config = CasbinConfig(
        app_name="file-based-rbac-example",
        superadmin_role=roles_config.get("superadmin_role", "admin")
    )
    
    # Add policies from configuration
    for policy_data in policies_config["policies"]:
        config.add_policy(
            policy_data["subject"],
            policy_data["object"],
            policy_data["action"]
        )
    
    return config


def setup_rbac() -> RBACService:
    """Setup the file-based RBAC system"""
    
    # Load roles configuration
    roles_config = config_manager.load_roles_config()
    role_names = [role["name"] for role in roles_config["roles"]]
    superadmin_role = roles_config.get("superadmin_role", "admin")
    
    # Create dynamic roles
    Role = create_roles(role_names)
    
    # Create RBAC configuration
    config = create_rbac_config()
    
    # Create providers
    subject_provider = DefaultSubjectProvider(field_name="email")
    role_provider = DefaultRoleProvider(superadmin_role=superadmin_role)
    
    # Create RBAC service
    rbac_service = RBACService(
        config=config,
        subject_provider=subject_provider,
        role_provider=role_provider
    )
    
    # Add user-role mappings to Casbin
    for user in USERS.values():
        rbac_service.enforcer.add_grouping_policy(user.email, user.role)
    
    # Register custom ownership providers
    ownership_providers = {
        "document": DocumentOwnershipProvider(superadmin_role=superadmin_role),
        "project": ProjectOwnershipProvider(superadmin_role=superadmin_role),
        "task": TaskOwnershipProvider(superadmin_role=superadmin_role),
    }
    
    for resource_type, provider in ownership_providers.items():
        rbac_service.ownership_registry.register(resource_type, provider)
    
    return rbac_service


# ============================================================================
# Authentication - Simple JWT Implementation
# ============================================================================

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
# FastAPI Application - File-Based Configuration
# ============================================================================

app = FastAPI(
    title="File-Based Configuration RBAC Example",
    description="Demonstrates pure general RBAC with file-based configuration",
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
# Configuration Endpoints
# ============================================================================

@app.get("/config", response_model=ConfigResponse)
async def get_configuration(current_user: UserModel = Depends(get_current_user)):
    """Get current RBAC configuration"""
    
    roles_config = config_manager.load_roles_config()
    policies_config = config_manager.load_policies_config()
    resources_config = config_manager.load_resources_config()
    
    return ConfigResponse(
        roles=roles_config["roles"],
        policies=policies_config["policies"],
        resource_types=resources_config["resource_types"]
    )


@app.get("/config/reload")
@require(Permission("system", "manage"))
async def reload_configuration(
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Reload configuration from files - admin only"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # In a real application, you would reload the RBAC service here
    # For this example, we'll just return a success message
    return MessageResponse(message="Configuration reloaded successfully")


# ============================================================================
# Resource Endpoints - File-Based Configuration
# ============================================================================

@app.get("/", response_model=MessageResponse)
async def root():
    """Root endpoint"""
    return MessageResponse(message="File-Based Configuration RBAC Example")


@app.get("/resources", response_model=List[ResourceResponse])
@require(Permission("*", "read"))
async def list_resources(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """List resources with file-based access control"""
    
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
            # Check all permissions for this resource
            permissions = {}
            for action in ["read", "create", "update", "delete", "share", "manage_members", "assign"]:
                permissions[f"can_{action}"] = await rbac.can_access(
                    current_user, 
                    resource.to_resource_ref(), 
                    action
                )
            
            accessible_resources.append(ResourceResponse(
                id=resource.id,
                type=resource.type,
                title=resource.title,
                owner_id=resource.owner_id,
                is_public=resource.is_public,
                metadata=resource.metadata,
                permissions=permissions
            ))
    
    return accessible_resources


@app.get("/resources/{resource_type}/{resource_id}", response_model=ResourceResponse)
@require(Permission("*", "read"))
async def get_resource(
    resource_type: str,
    resource_id: int,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Get specific resource with file-based access control"""
    
    # Find resource
    resource = next((r for r in RESOURCES if r.id == resource_id and r.type == resource_type), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Check access
    can_access = await rbac.can_access(current_user, resource.to_resource_ref(), "read")
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check all permissions for this resource
    permissions = {}
    for action in ["read", "create", "update", "delete", "share", "manage_members", "assign"]:
        permissions[f"can_{action}"] = await rbac.can_access(
            current_user, 
            resource.to_resource_ref(), 
            action
        )
    
    return ResourceResponse(
        id=resource.id,
        type=resource.type,
        title=resource.title,
        owner_id=resource.owner_id,
        is_public=resource.is_public,
        metadata=resource.metadata,
        permissions=permissions
    )


@app.post("/resources/{resource_type}", response_model=ResourceResponse)
@require(Permission("*", "create"))
async def create_resource(
    resource_type: str,
    request: ResourceCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Create new resource with file-based access control"""
    
    # Check if user can create this resource type
    can_create = await rbac.check_permission(current_user, resource_type, "create")
    if not can_create:
        raise HTTPException(status_code=403, detail=f"Cannot create {resource_type}")
    
    # Create new resource
    new_id = max([r.id for r in RESOURCES], default=0) + 1
    new_resource = GenericResource(
        id=new_id,
        type=resource_type,
        title=request.title,
        owner_id=current_user.id,
        is_public=request.is_public,
        metadata=request.metadata
    )
    
    RESOURCES.append(new_resource)
    
    # Check permissions for response
    permissions = {}
    for action in ["read", "create", "update", "delete", "share", "manage_members", "assign"]:
        permissions[f"can_{action}"] = await rbac.can_access(
            current_user, 
            new_resource.to_resource_ref(), 
            action
        )
    
    return ResourceResponse(
        id=new_resource.id,
        type=new_resource.type,
        title=new_resource.title,
        owner_id=new_resource.owner_id,
        is_public=new_resource.is_public,
        metadata=new_resource.metadata,
        permissions=permissions
    )


@app.put("/resources/{resource_type}/{resource_id}", response_model=ResourceResponse)
@require(Permission("*", "update"))
async def update_resource(
    resource_type: str,
    resource_id: int,
    request: ResourceCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Update resource with file-based access control"""
    
    # Find resource
    resource = next((r for r in RESOURCES if r.id == resource_id and r.type == resource_type), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Check access
    can_update = await rbac.can_access(current_user, resource.to_resource_ref(), "update")
    if not can_update:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update resource
    resource.title = request.title
    resource.is_public = request.is_public
    if request.metadata:
        resource.metadata = request.metadata
    
    # Check permissions for response
    permissions = {}
    for action in ["read", "create", "update", "delete", "share", "manage_members", "assign"]:
        permissions[f"can_{action}"] = await rbac.can_access(
            current_user, 
            resource.to_resource_ref(), 
            action
        )
    
    return ResourceResponse(
        id=resource.id,
        type=resource.type,
        title=resource.title,
        owner_id=resource.owner_id,
        is_public=resource.is_public,
        metadata=resource.metadata,
        permissions=permissions
    )


@app.delete("/resources/{resource_type}/{resource_id}", response_model=MessageResponse)
@require(Permission("*", "delete"))
async def delete_resource(
    resource_type: str,
    resource_id: int,
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Delete resource with file-based access control"""
    
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
# Admin Endpoints - File-Based Configuration
# ============================================================================

@app.get("/admin/users", response_model=List[UserModel])
@require(Permission("user", "read"))
async def list_users(
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """List all users - admin only"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return list(USERS.values())


@app.get("/admin/stats", response_model=Dict[str, Any])
@require(Permission("system", "read"))
async def get_system_stats(
    current_user: UserModel = Depends(get_current_user),
    rbac: RBACService = Depends(lambda: rbac_service)
):
    """Get system statistics - admin only"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Load resource types from configuration
    resources_config = config_manager.load_resources_config()
    resource_types = [rt["name"] for rt in resources_config["resource_types"]]
    
    # Count resources by type
    resource_counts = {}
    for resource_type in resource_types:
        resource_counts[resource_type] = len([r for r in RESOURCES if r.type == resource_type])
    
    return {
        "total_users": len(USERS),
        "total_resources": len(RESOURCES),
        "resource_counts": resource_counts,
        "resource_types": resource_types,
        "cache_stats": rbac.get_cache_stats(),
        "config_files": {
            "roles": str(ROLES_CONFIG_FILE),
            "policies": str(POLICIES_CONFIG_FILE),
            "resources": str(RESOURCES_CONFIG_FILE),
            "users": str(USERS_CONFIG_FILE)
        }
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("File-Based Configuration RBAC Example")
    print("=" * 70)
    print("This example demonstrates:")
    print("- Configuration-driven role and policy definition")
    print("- Multiple generic resource types")
    print("- Custom ownership providers")
    print("- File-based policy storage")
    print("- YAML configuration files")
    print()
    print("Configuration files created in:", CONFIG_DIR)
    print("- roles.yaml: Role definitions and permissions")
    print("- policies.yaml: Access control policies")
    print("- resources.yaml: Resource type configurations")
    print("- users.yaml: User definitions and attributes")
    print()
    print("Test users:")
    for email, user in USERS.items():
        print(f"  {email} (role: {user.role}, password: password)")
    print()
    print("Starting server at http://localhost:8001")
    print("API docs at http://localhost:8001/docs")
    print("=" * 70)
    
    uvicorn.run(
        "file_based_rbac_example:app",
        host="0.0.0.0",
        port=8001,
        reload=False
    )