# Design Document: Pure General RBAC System

## Overview

This design document outlines the architecture for completing the transformation of fastapi-role into a pure general RBAC engine. The system must be completely business-agnostic, working with any resource type and domain without hardcoded assumptions. The focus is on removing all business coupling while maintaining full functionality through configurable providers and data-driven policies.

## Architecture

### Pure General RBAC Architecture

The target architecture eliminates all business-specific concepts and provides a truly generic RBAC engine:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pure General RBAC Engine                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Core RBAC Engine                        │   │
│  │                                                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │   │
│  │  │ Dynamic     │ │ Resource    │ │ Privilege       │   │   │
│  │  │ Roles       │ │ Agnostic    │ │ Evaluation      │   │   │
│  │  │             │ │ Access      │ │                 │   │   │
│  │  │ create_roles│ │ can_access  │ │ evaluate        │   │   │
│  │  │ (names)     │ │ (user,res,  │ │ (user,          │   │   │
│  │  │             │ │  action)    │ │  privilege)     │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                │                                │
│  ┌─────────────────────────────┴─────────────────────────────┐ │
│  │                  Provider Architecture                    │ │
│  │                                                           │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Subject     │ │ Ownership   │ │ Policy              │ │ │
│  │  │ Provider    │ │ Provider    │ │ Provider            │ │ │
│  │  │             │ │             │ │                     │ │ │
│  │  │ extract_id  │ │ check_owns  │ │ load_policies       │ │ │
│  │  │ (user)      │ │ (user,type, │ │ (config)            │ │ │
│  │  │             │ │  id)        │ │                     │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                │                                │
│  ┌─────────────────────────────┴─────────────────────────────┐ │
│  │              Configuration System                         │ │
│  │                                                           │ │
│  │  • No hardcoded roles or resources                       │ │
│  │  • Data-driven policy definitions                        │ │
│  │  • Pluggable storage backends                            │ │
│  │  • Runtime role and privilege definition                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ User implements
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    User Application Domain                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Business-Specific Implementations            │ │
│  │                                                           │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Domain      │ │ Custom      │ │ Business            │ │ │
│  │  │ Models      │ │ Ownership   │ │ Policies            │ │ │
│  │  │             │ │ Rules       │ │                     │ │ │
│  │  │ User, Order,│ │ OrderOwner, │ │ roles.yaml,         │ │ │
│  │  │ Project,    │ │ ProjectMgr, │ │ policies.csv        │ │ │
│  │  │ etc.        │ │ TenantAdmin │ │                     │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Resource-Agnostic Access Control

The core principle is that the RBAC engine never knows what resources represent:

```
┌─────────────────────────────────────────────────────────────────┐
│                Resource-Agnostic Design                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ❌ Business-Coupled (Current)    ✅ Resource-Agnostic (Target) │
│   ─────────────────────────────    ──────────────────────────── │
│                                                                 │
│   get_accessible_customers()       can_access(user, resource,   │
│   get_accessible_orders()            action)                    │
│   get_accessible_projects()                                     │
│                                    evaluate(user, privilege)    │
│   check_customer_ownership()                                    │
│   check_order_ownership()          resolve_permissions(user)    │
│   check_project_ownership()                                     │
│                                                                 │
│   Hardcoded entity types           Generic (type, id) tuples    │
│   Business-specific queries        Pluggable ownership providers│
│   Compile-time assumptions         Runtime configuration        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Business Coupling Removal

#### Current Problematic Code Patterns
```python
# ❌ These patterns must be eliminated:

# Hardcoded business roles
class Role(Enum):
    SUPERADMIN = "superadmin"
    SALESMAN = "salesman"
    CUSTOMER = "customer"

# Business-specific access methods
async def get_accessible_customers(self, user: UserProtocol) -> list[int]:
    # Assumes customer concept exists
    
# Hardcoded resource types
if resource_type == "customer":
    from app.models.customer import Customer
    # Business model import

# Business exception imports
from app.core.exceptions import CustomerNotFoundError
```

#### Target Generic Patterns
```python
# ✅ Pure general RBAC patterns:

# Dynamic role creation
Role = create_roles(["admin", "manager", "user"], superadmin="admin")

# Resource-agnostic access
async def can_access(self, user: UserProtocol, resource: ResourceRef, action: str) -> bool:
    # Works with any resource type
    
# Generic resource reference
@dataclass
class ResourceRef:
    type: str  # "order", "project", "document", etc.
    id: Any    # int, UUID, str, etc.
    
# Generic ownership checking
async def check_ownership(self, user: UserProtocol, resource: ResourceRef) -> bool:
    provider = self.ownership_registry.get_provider(resource.type)
    return await provider.check_ownership(user, resource.type, resource.id)
```

### 2. Dynamic Role System Implementation

#### Role Factory Architecture
```python
# fastapi_role/core/roles.py
class RoleFactory:
    """Factory for creating dynamic role enums"""
    
    @staticmethod
    def create_roles(
        role_names: List[str],
        superadmin: Optional[str] = None,
        validate: bool = True
    ) -> Type[Enum]:
        """Create a dynamic role enum from role names"""
        
        if validate:
            RoleFactory._validate_role_names(role_names)
            
        # Create enum class with bitwise operations
        role_dict = {name.upper(): name.lower() for name in role_names}
        
        # Add composition support
        def __or__(self, other):
            return RoleComposition([self, other])
            
        def __ror__(self, other):
            return RoleComposition([other, self])
            
        role_dict['__or__'] = __or__
        role_dict['__ror__'] = __ror__
        
        # Create the enum
        RoleEnum = Enum('Role', role_dict)
        
        # Register superadmin if specified
        if superadmin:
            RoleRegistry.register_superadmin(RoleEnum, superadmin)
            
        return RoleEnum
        
    @staticmethod
    def _validate_role_names(names: List[str]) -> None:
        """Validate role names for correctness"""
        if not names:
            raise ValueError("Role names cannot be empty")
            
        for name in names:
            if not name or not name.strip():
                raise ValueError(f"Invalid role name: '{name}'")
            if not name.replace('_', '').replace('-', '').isalnum():
                raise ValueError(f"Role name contains invalid characters: '{name}'")
                
        if len(names) != len(set(names)):
            raise ValueError("Duplicate role names found")

class RoleRegistry:
    """Registry for managing dynamic roles"""
    
    _active_roles: Optional[Type[Enum]] = None
    _superadmin_role: Optional[str] = None
    
    @classmethod
    def register_roles(cls, role_enum: Type[Enum], superadmin: Optional[str] = None):
        """Register the active role enum"""
        cls._active_roles = role_enum
        cls._superadmin_role = superadmin
        
    @classmethod
    def is_superadmin(cls, role_value: str) -> bool:
        """Check if a role value is the superadmin role"""
        return cls._superadmin_role and role_value == cls._superadmin_role
        
    @classmethod
    def validate_role(cls, role_value: str) -> bool:
        """Validate that a role value is registered"""
        if not cls._active_roles:
            return False
        return any(role.value == role_value for role in cls._active_roles)
```

### 3. Resource-Agnostic Access Control

#### Generic Access Control Interface
```python
# fastapi_role/core/access.py
class ResourceRef:
    """Generic resource reference"""
    def __init__(self, type: str, id: Any, metadata: Optional[Dict] = None):
        self.type = type
        self.id = id
        self.metadata = metadata or {}
        
    def __str__(self) -> str:
        return f"{self.type}:{self.id}"

class AccessController:
    """Resource-agnostic access control"""
    
    def __init__(self, rbac_service: 'RBACService'):
        self.rbac_service = rbac_service
        
    async def can_access(
        self, 
        user: UserProtocol, 
        resource: ResourceRef, 
        action: str,
        context: Optional[Dict] = None
    ) -> bool:
        """Check if user can access resource with action"""
        
        # Check permission via policy engine
        permission_allowed = await self.rbac_service.check_permission(
            user, resource.type, action, context
        )
        
        if not permission_allowed:
            return False
            
        # Check ownership if required
        ownership_required = await self._requires_ownership(resource.type, action)
        if ownership_required:
            return await self.rbac_service.check_ownership(user, resource)
            
        return True
        
    async def evaluate(self, user: UserProtocol, privilege: 'Privilege') -> bool:
        """Evaluate a privilege against user"""
        
        # Check role requirements
        if privilege.roles:
            role_allowed = await self._check_roles(user, privilege.roles)
            if not role_allowed:
                return False
                
        # Check permission requirements
        if privilege.permission:
            perm_allowed = await self.rbac_service.check_permission(
                user, 
                privilege.permission.resource,
                privilege.permission.action,
                privilege.permission.context
            )
            if not perm_allowed:
                return False
                
        # Check ownership requirements
        if privilege.resource_ownership:
            ownership_allowed = await self.rbac_service.check_ownership(
                user, 
                ResourceRef(
                    privilege.resource_ownership.resource_type,
                    privilege.resource_ownership.extract_id(user)
                )
            )
            if not ownership_allowed:
                return False
                
        return True
        
    async def resolve_permissions(self, user: UserProtocol) -> Dict[str, List[str]]:
        """Resolve all permissions for a user"""
        
        # Get user's effective roles
        user_roles = await self.rbac_service.get_user_roles(user)
        
        # Query policy engine for all permissions
        all_permissions = {}
        for role in user_roles:
            role_permissions = await self.rbac_service.get_role_permissions(role)
            for resource_type, actions in role_permissions.items():
                if resource_type not in all_permissions:
                    all_permissions[resource_type] = set()
                all_permissions[resource_type].update(actions)
                
        # Convert sets to lists
        return {k: list(v) for k, v in all_permissions.items()}
```

### 4. Configurable Privilege System

#### Data-Driven Privilege Evaluation
```python
# fastapi_role/core/privilege.py
@dataclass
class PrivilegeDefinition:
    """Data structure for privilege definitions"""
    name: str
    description: str
    roles: Optional[List[str]] = None
    permissions: Optional[List[Dict[str, str]]] = None  # [{"resource": "order", "action": "read"}]
    ownership_required: Optional[List[str]] = None  # ["order", "project"]
    conditions: Optional[Dict[str, Any]] = None  # Additional conditions
    
class PrivilegeEvaluator:
    """Evaluates privileges based on data definitions"""
    
    def __init__(self, rbac_service: 'RBACService'):
        self.rbac_service = rbac_service
        self.privilege_definitions: Dict[str, PrivilegeDefinition] = {}
        
    def register_privilege(self, privilege: PrivilegeDefinition):
        """Register a privilege definition"""
        self.privilege_definitions[privilege.name] = privilege
        
    async def evaluate_privilege(
        self, 
        user: UserProtocol, 
        privilege_name: str,
        context: Optional[Dict] = None
    ) -> bool:
        """Evaluate a privilege by name"""
        
        privilege_def = self.privilege_definitions.get(privilege_name)
        if not privilege_def:
            raise ValueError(f"Unknown privilege: {privilege_name}")
            
        # Check role requirements
        if privilege_def.roles:
            user_role = await self.rbac_service.get_user_role(user)
            if user_role not in privilege_def.roles:
                # Check if user has superadmin bypass
                if not await self.rbac_service.is_superadmin(user):
                    return False
                    
        # Check permission requirements
        if privilege_def.permissions:
            for perm in privilege_def.permissions:
                allowed = await self.rbac_service.check_permission(
                    user, perm["resource"], perm["action"], context
                )
                if not allowed:
                    return False
                    
        # Check ownership requirements
        if privilege_def.ownership_required and context:
            for resource_type in privilege_def.ownership_required:
                resource_id = context.get(f"{resource_type}_id")
                if resource_id:
                    resource = ResourceRef(resource_type, resource_id)
                    allowed = await self.rbac_service.check_ownership(user, resource)
                    if not allowed:
                        return False
                        
        # Check additional conditions
        if privilege_def.conditions:
            allowed = await self._evaluate_conditions(
                user, privilege_def.conditions, context
            )
            if not allowed:
                return False
                
        return True
        
    async def _evaluate_conditions(
        self, 
        user: UserProtocol, 
        conditions: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> bool:
        """Evaluate additional conditions"""
        
        # This can be extended to support complex condition evaluation
        # For now, implement basic attribute-based conditions
        
        for condition_type, condition_value in conditions.items():
            if condition_type == "user_attribute":
                attr_name, expected_value = condition_value["name"], condition_value["value"]
                actual_value = getattr(user, attr_name, None)
                if actual_value != expected_value:
                    return False
                    
            elif condition_type == "context_attribute":
                attr_name, expected_value = condition_value["name"], condition_value["value"]
                if not context or context.get(attr_name) != expected_value:
                    return False
                    
        return True
```

### 5. Provider Architecture Enhancement

#### Complete Provider System
```python
# fastapi_role/protocols/providers.py
from typing import Protocol, Any, Dict, List, Optional
from abc import abstractmethod

class SubjectProvider(Protocol):
    """Provider for extracting user subjects for Casbin"""
    
    @abstractmethod
    def get_subject(self, user: UserProtocol) -> str:
        """Extract subject identifier from user"""
        ...

class RoleProvider(Protocol):
    """Provider for user role resolution"""
    
    @abstractmethod
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        """Get all roles for a user"""
        ...
        
    @abstractmethod
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        """Check if user has specific role"""
        ...

class OwnershipProvider(Protocol):
    """Provider for resource ownership validation"""
    
    @abstractmethod
    async def check_ownership(
        self, 
        user: UserProtocol, 
        resource_type: str, 
        resource_id: Any
    ) -> bool:
        """Check if user owns the resource"""
        ...

class PolicyProvider(Protocol):
    """Provider for policy loading and management"""
    
    @abstractmethod
    async def load_policies(self) -> List[List[str]]:
        """Load policy rules"""
        ...
        
    @abstractmethod
    async def save_policy(self, policy: List[str]) -> bool:
        """Save a policy rule"""
        ...
        
    @abstractmethod
    async def remove_policy(self, policy: List[str]) -> bool:
        """Remove a policy rule"""
        ...

class CacheProvider(Protocol):
    """Provider for caching authorization results"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        ...
        
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL"""
        ...
        
    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries"""
        ...
        
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        ...

# Default implementations
class DefaultSubjectProvider:
    """Default subject provider using user.email"""
    
    def __init__(self, field_name: str = "email"):
        self.field_name = field_name
        
    def get_subject(self, user: UserProtocol) -> str:
        return getattr(user, self.field_name)

class DefaultRoleProvider:
    """Default role provider using user.role"""
    
    def __init__(self, superadmin_role: Optional[str] = None):
        self.superadmin_role = superadmin_role
        
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        role = getattr(user, 'role', None)
        return [role] if role else []
        
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        user_role = getattr(user, 'role', None)
        if user_role == role_name:
            return True
        # Check superadmin bypass
        if self.superadmin_role and user_role == self.superadmin_role:
            return True
        return False

class DefaultOwnershipProvider:
    """Default ownership provider with superadmin bypass"""
    
    def __init__(
        self, 
        superadmin_role: Optional[str] = None,
        default_allow: bool = False
    ):
        self.superadmin_role = superadmin_role
        self.default_allow = default_allow
        
    async def check_ownership(
        self, 
        user: UserProtocol, 
        resource_type: str, 
        resource_id: Any
    ) -> bool:
        # Check superadmin bypass
        if self.superadmin_role:
            user_role = getattr(user, 'role', None)
            if user_role == self.superadmin_role:
                return True
                
        # Default behavior
        return self.default_allow
```

## Data Models

### Generic Resource Models

#### Resource Reference System
```python
@dataclass
class ResourceRef:
    """Generic resource reference - works with any domain"""
    type: str  # "order", "project", "document", "user", etc.
    id: Any    # int, UUID, str, composite key, etc.
    metadata: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"{self.type}:{self.id}"
        
    def __hash__(self) -> int:
        return hash((self.type, str(self.id)))

@dataclass 
class Permission:
    """Generic permission - no business assumptions"""
    resource: str  # Generic resource type
    action: str    # Generic action
    context: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"

@dataclass
class Privilege:
    """Generic privilege bundle"""
    name: str
    roles: Optional[List[str]] = None
    permissions: Optional[List[Permission]] = None
    ownership_required: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
```

### Configuration Models

#### Pure Configuration System
```python
@dataclass
class RBACConfig:
    """Configuration with no business assumptions"""
    
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
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'RBACConfig':
        """Create config from dictionary"""
        return cls(**config_dict)
        
    @classmethod
    def from_env(cls, prefix: str = "RBAC_") -> 'RBACConfig':
        """Create config from environment variables"""
        import os
        config = {}
        
        # Map environment variables to config fields
        env_mapping = {
            f"{prefix}ROLES": "roles",
            f"{prefix}SUPERADMIN_ROLE": "superadmin_role",
            f"{prefix}MODEL_PATH": "model_path",
            f"{prefix}POLICY_PATH": "policy_path",
            f"{prefix}CACHE_ENABLED": "cache_enabled",
            f"{prefix}CACHE_TTL": "cache_ttl_seconds",
            f"{prefix}DEFAULT_DENY": "default_deny",
            f"{prefix}LOG_DENIALS": "log_denials",
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion based on field
                if config_key == "roles":
                    config[config_key] = value.split(",")
                elif config_key in ["cache_enabled", "default_deny", "log_denials"]:
                    config[config_key] = value.lower() in ("true", "1", "yes")
                elif config_key == "cache_ttl_seconds":
                    config[config_key] = int(value)
                else:
                    config[config_key] = value
                    
        return cls(**config)
        
    def validate(self) -> None:
        """Validate configuration consistency"""
        if self.roles and self.superadmin_role:
            if self.superadmin_role not in self.roles:
                raise ValueError(f"Superadmin role '{self.superadmin_role}' not in roles list")
                
        if not self.model_path and not self.model_text:
            # Use default embedded model
            self.model_text = self._get_default_model()
            
        if self.cache_ttl_seconds <= 0:
            raise ValueError("Cache TTL must be positive")
            
    def _get_default_model(self) -> str:
        """Get default RBAC model"""
        return """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Business Coupling Elimination
*For any* RBAC operation, the system should never reference business-specific models, roles, or concepts.
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

### Property 2: Resource Type Agnosticism  
*For any* resource type string and resource ID, the system should handle access control without knowing what the resource represents.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

### Property 3: Dynamic Role Consistency
*For any* valid list of role names, creating roles multiple times with the same configuration should produce equivalent enum classes with identical behavior.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

### Property 4: Privilege Evaluation Determinism
*For any* user, privilege definition, and context, multiple evaluations should always return the same result.
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**

### Property 5: Customer Concept Absence
*For any* RBAC operation, the system should never assume or require customer-specific concepts or data structures.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**

### Property 6: Ownership Provider Delegation
*For any* resource type and ownership check, the system should delegate to registered providers without performing business-specific logic.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7**

### Property 7: Provider Architecture Completeness
*For any* provider type (Subject, Role, Ownership, Cache, Policy), the system should support registration, validation, and graceful error handling.
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

### Property 8: Configuration Data-Driven Behavior
*For any* configuration source and values, the system behavior should be determined by the configuration data without code changes.
**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7**

### Property 9: Database Agnosticism
*For any* data storage backend, the system should function without requiring specific database connections or schemas.
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7**

### Property 10: Pure General RBAC Completeness
*For any* application domain, the RBAC system should provide complete access control functionality without domain-specific assumptions.
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7**

## Error Handling

### Generic Error System

The error handling system must be completely business-agnostic:

```python
# fastapi_role/exceptions.py
class RBACError(Exception):
    """Base exception for all RBAC errors - no business coupling"""
    def __init__(self, message: str, error_code: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)

class ConfigurationError(RBACError):
    """Configuration-related errors"""
    pass

class RoleDefinitionError(RBACError):
    """Role definition and creation errors"""
    pass

class ProviderError(RBACError):
    """Provider registration and execution errors"""
    pass

class AuthorizationError(RBACError):
    """Authorization check errors"""
    pass

class ResourceError(RBACError):
    """Resource reference and access errors"""
    pass

# No business-specific exceptions like CustomerNotFoundError
```

### Error Response Patterns

```python
# Generic error responses - no business assumptions
{
    "detail": "Access denied: insufficient privileges for resource access",
    "error_code": "AUTHORIZATION_DENIED", 
    "resource_type": "document",  # Generic
    "resource_id": "123",         # Generic
    "required_action": "read",    # Generic
    "user_roles": ["user"],       # Dynamic
    "context": {}                 # Extensible
}
```

## Testing Strategy

### Property-Based Testing for Pure General RBAC

The testing strategy focuses on verifying that the system is truly business-agnostic:

```python
from hypothesis import given, strategies as st

class PureRBACProperties:
    """Properties that verify business coupling elimination"""
    
    @given(
        resource_types=st.lists(st.text(min_size=1), min_size=1, max_size=10),
        resource_ids=st.lists(st.integers() | st.text() | st.uuids(), min_size=1),
        actions=st.lists(st.text(min_size=1), min_size=1, max_size=5)
    )
    def test_resource_type_agnosticism(self, resource_types, resource_ids, actions):
        """System works with arbitrary resource types"""
        # Test that system handles any resource type without hardcoded assumptions
        
    @given(
        role_names=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: x.isalnum()),
            min_size=1, max_size=20, unique=True
        )
    )
    def test_dynamic_role_creation(self, role_names):
        """Dynamic role creation works with any valid role names"""
        # Test role creation with arbitrary role names
        
    @given(
        user_data=st.fixed_dictionaries({
            'id': st.integers() | st.uuids() | st.text(),
            'email': st.emails(),
            'role': st.text(min_size=1)
        })
    )
    def test_user_protocol_compliance(self, user_data):
        """System works with any UserProtocol-compliant object"""
        # Test with various user implementations
```

### Integration Testing with Generic Applications

```python
# Test applications that demonstrate business agnosticism
class GenericTestApplication:
    """Test app with arbitrary domain concepts"""
    
    def __init__(self, domain_config: Dict[str, Any]):
        # Configure with arbitrary business domain
        self.resource_types = domain_config["resource_types"]  # ["order", "project", "task"]
        self.roles = domain_config["roles"]                    # ["admin", "manager", "user"]
        self.actions = domain_config["actions"]                # ["create", "read", "update", "delete"]
        
    def test_arbitrary_domain_integration(self):
        """Test that RBAC works with any business domain"""
        # Verify system works regardless of domain concepts
```

This design ensures the fastapi-role package becomes a truly pure general RBAC engine that can be used in any application domain without business coupling or hardcoded assumptions.