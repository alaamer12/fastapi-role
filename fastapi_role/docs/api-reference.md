# API Reference

Complete API reference for fastapi-role Pure General RBAC Engine.

## Core Classes

### RBACService

The main RBAC service providing all authorization functionality.

```python
class RBACService:
    """Pure General RBAC Service with zero business assumptions."""
    
    def __init__(
        self,
        config: Optional[CasbinConfig] = None,
        subject_provider: Optional[SubjectProvider] = None,
        role_provider: Optional[RoleProvider] = None,
        cache_provider: Optional[CacheProvider] = None
    ):
        """Initialize RBAC service with optional providers."""
```

#### Methods

##### `can_access(user, resource, action) -> bool`

Check if user can access resource with specific action.

```python
async def can_access(
    self,
    user: UserProtocol,
    resource: ResourceRef,
    action: str,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Check if user can access resource with action.
    
    Args:
        user: User implementing UserProtocol
        resource: Resource reference (type, id)
        action: Action to perform (read, write, delete, etc.)
        context: Optional context for evaluation
        
    Returns:
        True if access allowed, False otherwise
        
    Example:
        >>> resource = ResourceRef("document", 123)
        >>> allowed = await rbac.can_access(user, resource, "read")
    """
```

##### `evaluate(user, privilege) -> bool`

Evaluate a privilege against a user.

```python
async def evaluate(
    self,
    user: UserProtocol,
    privilege: Privilege,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Evaluate privilege against user.
    
    Args:
        user: User implementing UserProtocol
        privilege: Privilege definition to evaluate
        context: Optional context for evaluation
        
    Returns:
        True if privilege granted, False otherwise
        
    Example:
        >>> privilege = Privilege(
        ...     roles=[Role.ADMIN],
        ...     permissions=[Permission("document", "read")]
        ... )
        >>> granted = await rbac.evaluate(user, privilege)
    """
```

##### `check_ownership(user, resource) -> bool`

Check if user owns a resource.

```python
async def check_ownership(
    self,
    user: UserProtocol,
    resource: ResourceRef
) -> bool:
    """
    Check if user owns the resource.
    
    Args:
        user: User implementing UserProtocol
        resource: Resource reference to check
        
    Returns:
        True if user owns resource, False otherwise
        
    Example:
        >>> resource = ResourceRef("project", 456)
        >>> owns = await rbac.check_ownership(user, resource)
    """
```

##### `register_ownership_provider(resource_type, provider)`

Register ownership provider for specific resource type.

```python
def register_ownership_provider(
    self,
    resource_type: str,
    provider: OwnershipProvider
) -> None:
    """
    Register ownership provider for resource type.
    
    Args:
        resource_type: Type of resource (e.g., "project", "document")
        provider: Provider implementing OwnershipProvider protocol
        
    Example:
        >>> rbac.register_ownership_provider("project", ProjectOwnershipProvider())
    """
```

### Dynamic Role Creation

#### `create_roles(role_names, superadmin=None) -> Type[Enum]`

Create dynamic role enum at runtime.

```python
def create_roles(
    role_names: List[str],
    superadmin: Optional[str] = None,
    validate: bool = True
) -> Type[Enum]:
    """
    Create dynamic role enum from role names.
    
    Args:
        role_names: List of role names to create
        superadmin: Optional superadmin role name
        validate: Whether to validate role names
        
    Returns:
        Dynamic enum class with role values
        
    Raises:
        ValueError: If role names are invalid or duplicated
        
    Example:
        >>> Role = create_roles(["admin", "manager", "user"], superadmin="admin")
        >>> Role.ADMIN.value
        'admin'
        >>> Role.MANAGER | Role.USER  # Role composition
        RoleComposition([Role.MANAGER, Role.USER])
    """
```

## Data Models

### ResourceRef

Generic resource reference for any domain.

```python
@dataclass
class ResourceRef:
    """Generic resource reference - works with any domain."""
    
    type: str  # Resource type (e.g., "order", "project", "document")
    id: Any    # Resource ID (int, UUID, str, composite key, etc.)
    metadata: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"{self.type}:{self.id}"
        
    def __hash__(self) -> int:
        return hash((self.type, str(self.id)))
```

**Examples:**
```python
# Different resource types
document = ResourceRef("document", 123)
project = ResourceRef("project", "proj-uuid-456")
user_profile = ResourceRef("user_profile", user.id)
spaceship = ResourceRef("spaceship", "enterprise-nx01")
```

### Permission

Generic permission model.

```python
@dataclass
class Permission:
    """Generic permission - no business assumptions."""
    
    resource: str  # Generic resource type
    action: str    # Generic action
    context: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"
```

**Examples:**
```python
# Various permission types
read_docs = Permission("document", "read")
launch_ship = Permission("spaceship", "launch")
cook_recipe = Permission("recipe", "cook")
manage_quantum = Permission("quantum_computer", "entangle")
```

### Privilege

Configurable privilege bundle.

```python
@dataclass
class Privilege:
    """Generic privilege bundle."""
    
    name: str
    roles: Optional[List[str]] = None
    permissions: Optional[List[Permission]] = None
    ownership_required: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
```

**Example:**
```python
admin_privilege = Privilege(
    name="admin_access",
    roles=["admin", "superuser"],
    permissions=[
        Permission("*", "*"),  # All resources, all actions
    ],
    ownership_required=[],  # No ownership required for admin
    conditions={"active": True}
)

manager_privilege = Privilege(
    name="manager_access",
    roles=["manager"],
    permissions=[
        Permission("project", "read"),
        Permission("project", "write"),
        Permission("team", "manage")
    ],
    ownership_required=["project"],  # Must own project
    conditions={"department": "engineering"}
)
```

## Decorators

### `@require`

Framework-agnostic decorator for protecting functions.

```python
def require(*requirements: Union[str, Permission, Privilege]) -> Callable:
    """
    Protect function with RBAC requirements.
    
    Args:
        *requirements: Role names, Permission objects, or Privilege objects
        
    Returns:
        Decorated function with RBAC protection
        
    Behavior:
        - Multiple @require decorators use OR logic
        - Multiple requirements in one @require use AND logic
        - Supports dependency injection for RBACService
        
    Examples:
        # Single role requirement
        @require(Role.ADMIN)
        async def admin_function(user: User, rbac: RBACService):
            pass
            
        # Multiple requirements (AND logic)
        @require(Role.MANAGER, Permission("project", "delete"))
        async def delete_project(project_id: int, user: User, rbac: RBACService):
            pass
            
        # Multiple decorators (OR logic)
        @require(Role.ADMIN)
        @require(Role.MANAGER, Permission("project", "manage"))
        async def manage_project(project_id: int, user: User, rbac: RBACService):
            pass
    """
```

#### Service Injection Patterns

The `@require` decorator supports multiple service injection patterns:

```python
# Pattern 1: Explicit service parameter
@require(Role.ADMIN)
async def admin_function(user: User, rbac_service: RBACService):
    pass

# Pattern 2: FastAPI dependency injection
@require(Role.ADMIN)
async def admin_function(
    user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    pass

# Pattern 3: Context-based injection (custom)
@require(Role.ADMIN)
async def admin_function(user: User):
    # Service resolved from context
    pass
```

## Provider Protocols

### UserProtocol

Protocol that user models must implement.

```python
class UserProtocol(Protocol):
    """Protocol for user objects."""
    
    @property
    def id(self) -> Any:
        """User identifier."""
        ...
        
    @property
    def role(self) -> str:
        """User role."""
        ...
```

**Implementation Example:**
```python
@dataclass
class User:
    id: int
    email: str
    role: str
    tenant_id: Optional[int] = None
    
    # Automatically implements UserProtocol
```

### SubjectProvider

Provider for extracting user subjects for Casbin.

```python
class SubjectProvider(Protocol):
    """Provider for extracting user subjects for Casbin."""
    
    @abstractmethod
    def get_subject(self, user: UserProtocol) -> str:
        """Extract subject identifier from user."""
        ...
```

**Implementation Example:**
```python
class TenantSubjectProvider:
    def get_subject(self, user: UserProtocol) -> str:
        return f"user:{user.id}:tenant:{user.tenant_id}"
```

### RoleProvider

Provider for user role resolution.

```python
class RoleProvider(Protocol):
    """Provider for user role resolution."""
    
    @abstractmethod
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        """Get all roles for a user."""
        ...
        
    @abstractmethod
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        """Check if user has specific role."""
        ...
```

**Implementation Example:**
```python
class DatabaseRoleProvider:
    def __init__(self, db_session):
        self.db = db_session
        
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        # Query database for user roles
        roles = await self.db.query(UserRole).filter_by(user_id=user.id).all()
        return [role.name for role in roles]
        
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        roles = await self.get_user_roles(user)
        return role_name in roles
```

### OwnershipProvider

Provider for resource ownership validation.

```python
class OwnershipProvider(Protocol):
    """Provider for resource ownership validation."""
    
    @abstractmethod
    async def check_ownership(
        self, 
        user: UserProtocol, 
        resource_type: str, 
        resource_id: Any
    ) -> bool:
        """Check if user owns the resource."""
        ...
```

**Implementation Examples:**
```python
class ProjectOwnershipProvider:
    def __init__(self, db_session):
        self.db = db_session
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "project":
            project = await self.db.get(Project, resource_id)
            return project and (
                project.owner_id == user.id or 
                user.id in project.collaborator_ids
            )
        return False

class MultiTenantOwnershipProvider:
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        # For multi-tenant apps, check tenant ownership
        if hasattr(user, 'tenant_id'):
            resource = await get_resource(resource_type, resource_id)
            return resource and resource.tenant_id == user.tenant_id
        return False
```

### CacheProvider

Provider for caching authorization results.

```python
class CacheProvider(Protocol):
    """Provider for caching authorization results."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
        
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        ...
        
    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries."""
        ...
```

**Implementation Example:**
```python
class RedisCacheProvider:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self.redis.set(key, json.dumps(value), ex=ttl)
        
    async def clear(self, pattern: Optional[str] = None) -> None:
        if pattern:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        else:
            await self.redis.flushdb()
```

## Configuration

### CasbinConfig

Configuration class for RBAC behavior.

```python
@dataclass
class CasbinConfig:
    """Configuration with no business assumptions."""
    
    # Role configuration - completely dynamic
    roles: Optional[List[str]] = None
    superadmin_role: Optional[str] = None
    
    # Policy configuration - pluggable
    model_path: Optional[str] = None
    model_text: Optional[str] = None
    policy_path: Optional[str] = None
    policy_adapter: Optional[Any] = None
    
    # Provider configuration - all pluggable
    subject_provider: Optional[SubjectProvider] = None
    role_provider: Optional[RoleProvider] = None
    ownership_providers: Optional[Dict[str, OwnershipProvider]] = None
    cache_provider: Optional[CacheProvider] = None
    
    # Behavior configuration - no business defaults
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    default_deny: bool = True
    log_denials: bool = True
```

**Configuration Examples:**
```python
# File-based configuration
config = CasbinConfig(
    model_path="rbac_model.conf",
    policy_path="policies.csv",
    roles=["admin", "manager", "user"],
    superadmin_role="admin"
)

# Environment-based configuration
config = CasbinConfig.from_env(prefix="RBAC_")

# Programmatic configuration
config = CasbinConfig(
    roles=["owner", "admin", "member"],
    superadmin_role="owner",
    cache_enabled=True,
    cache_ttl_seconds=600,
    subject_provider=CustomSubjectProvider(),
    ownership_providers={
        "project": ProjectOwnershipProvider(),
        "document": DocumentOwnershipProvider()
    }
)
```

## Exceptions

### RBACError

Base exception for all RBAC errors.

```python
class RBACError(Exception):
    """Base exception for all RBAC errors - no business coupling."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str, 
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)
```

### Specific Exceptions

```python
class ConfigurationError(RBACError):
    """Configuration-related errors."""
    pass

class RoleDefinitionError(RBACError):
    """Role definition and creation errors."""
    pass

class PermissionDeniedError(RBACError):
    """Permission denied errors."""
    pass

class ProviderError(RBACError):
    """Provider-related errors."""
    pass
```

## Utilities

### Query Helpers

Generic query filtering utilities.

```python
def filter_by_permissions(
    query: Any,
    user: UserProtocol,
    resource_type: str,
    action: str = "read"
) -> Any:
    """
    Filter query results by user permissions.
    
    Args:
        query: Database query object
        user: User to check permissions for
        resource_type: Type of resources being queried
        action: Action being performed
        
    Returns:
        Filtered query object
        
    Example:
        >>> query = session.query(Project)
        >>> filtered = filter_by_permissions(query, user, "project", "read")
    """
```

### Resource Helpers

```python
def extract_resource_id(obj: Any, id_field: str = "id") -> Any:
    """Extract resource ID from object."""
    return getattr(obj, id_field)

def create_resource_ref(obj: Any, resource_type: str, id_field: str = "id") -> ResourceRef:
    """Create ResourceRef from object."""
    return ResourceRef(resource_type, extract_resource_id(obj, id_field))
```

## Framework Integration

### FastAPI Integration

```python
from fastapi import Depends, FastAPI
from fastapi_role import RBACService, create_roles, require

app = FastAPI()
Role = create_roles(["admin", "user"])
rbac = RBACService()

def get_rbac_service() -> RBACService:
    return rbac

@require(Role.ADMIN)
async def admin_business_function(
    data: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    return {"message": f"Admin processed: {data}"}

@app.post("/admin/process")
async def admin_endpoint(
    data: ProcessRequest,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    return await admin_business_function(data.content, current_user, rbac_service)
```

### Flask Integration

```python
from flask import Flask, request, g
from fastapi_role import RBACService, create_roles, require

app = Flask(__name__)
Role = create_roles(["admin", "user"])
rbac = RBACService()

@require(Role.ADMIN)
async def admin_business_function(data: str, current_user: User, rbac_service: RBACService):
    return {"message": f"Admin processed: {data}"}

@app.route('/admin/process', methods=['POST'])
def admin_endpoint():
    current_user = get_current_user()  # Your auth logic
    data = request.json.get('data')
    
    result = asyncio.run(admin_business_function(data, current_user, rbac))
    return jsonify(result)
```

### CLI Integration

```python
import asyncio
import click
from fastapi_role import RBACService, create_roles, require

Role = create_roles(["admin", "operator"])
rbac = RBACService()

@require(Role.ADMIN)
async def backup_system(backup_type: str, current_user: User, rbac_service: RBACService):
    print(f"Starting {backup_type} backup...")
    return {"status": "backup_started", "type": backup_type}

@click.command()
@click.option('--backup-type', default='full')
def backup_command(backup_type):
    admin_user = User(id=1, role="admin")  # Get from auth
    result = asyncio.run(backup_system(backup_type, admin_user, rbac))
    click.echo(f"Backup result: {result}")

if __name__ == '__main__':
    backup_command()
```

## Best Practices

### 1. Resource-Agnostic Design

```python
# ❌ DON'T: Business-specific methods
rbac.get_accessible_customers(user)
rbac.check_order_ownership(user, order_id)

# ✅ DO: Resource-agnostic methods
rbac.can_access(user, ResourceRef("customer", customer_id), "read")
rbac.check_ownership(user, ResourceRef("order", order_id))
```

### 2. Dynamic Role Creation

```python
# ❌ DON'T: Hardcoded roles
class Role(Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"

# ✅ DO: Dynamic roles
Role = create_roles(["admin", "manager", "user"], superadmin="admin")
```

### 3. Provider-Based Customization

```python
# ✅ DO: Use providers for business logic
class CustomOwnershipProvider:
    async def check_ownership(self, user, resource_type, resource_id):
        # Your custom ownership logic
        return True

rbac.register_ownership_provider("project", CustomOwnershipProvider())
```

### 4. Framework-Agnostic Functions

```python
# ✅ DO: Protect business functions, not endpoints
@require(Role.ADMIN, Permission("users", "delete"))
async def delete_user_business_logic(user_id: int, current_user: User, rbac: RBACService):
    # Business logic here - works with any framework
    pass

# Then call from any framework
@app.delete("/users/{user_id}")  # FastAPI
async def delete_user_endpoint(user_id: int, ...):
    return await delete_user_business_logic(user_id, current_user, rbac)
```

### 5. Configuration-Driven Behavior

```python
# ✅ DO: Define behavior through configuration
config = CasbinConfig(
    roles=["admin", "user"],  # Dynamic
    superadmin_role="admin",  # Configurable
    cache_enabled=True,       # Behavior setting
    default_deny=True         # Security setting
)
```

This API reference provides complete documentation for using fastapi-role as a pure general RBAC engine with zero business assumptions.