# Provider Architecture

The provider architecture is the heart of fastapi-role's pure general RBAC design. It allows you to customize all business-specific behavior while keeping the core RBAC engine completely business-agnostic.

## 🎯 Philosophy

The core principle: **The RBAC engine never knows about your business domain**. All business-specific logic is implemented through pluggable providers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pure General RBAC Engine                     │
│  • Dynamic role creation                                        │
│  • Resource-agnostic access control                            │
│  • Generic privilege evaluation                                 │
│  • Framework-agnostic decorators                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Delegates all business logic
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Provider Architecture                        │
│  • SubjectProvider: How to identify users                      │
│  • RoleProvider: How to resolve user roles                     │
│  • OwnershipProvider: How to check resource ownership          │
│  • PolicyProvider: How to store and load policies              │
│  • CacheProvider: How to cache authorization results           │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Your implementations
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Your Business Domain                         │
│  • User models, database schemas, business rules               │
│  • Domain-specific ownership logic                             │
│  • Custom caching strategies                                   │
│  • Integration with existing systems                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🔌 Provider Types

### 1. SubjectProvider

Extracts user identifiers for Casbin policy evaluation.

```python
from fastapi_role.protocols import SubjectProvider

class SubjectProvider(Protocol):
    @abstractmethod
    def get_subject(self, user: UserProtocol) -> str:
        """Extract subject identifier from user."""
        ...
```

#### Default Implementation

```python
class DefaultSubjectProvider:
    def __init__(self, field_name: str = "email"):
        self.field_name = field_name
        
    def get_subject(self, user: UserProtocol) -> str:
        return getattr(user, self.field_name)
```

#### Custom Implementations

```python
# Simple ID-based subject
class IdSubjectProvider:
    def get_subject(self, user: UserProtocol) -> str:
        return f"user:{user.id}"

# Multi-tenant subject
class TenantSubjectProvider:
    def get_subject(self, user: UserProtocol) -> str:
        return f"user:{user.id}:tenant:{user.tenant_id}"

# Department-based subject
class DepartmentSubjectProvider:
    def get_subject(self, user: UserProtocol) -> str:
        return f"user:{user.id}:dept:{user.department}"

# Complex hierarchical subject
class HierarchicalSubjectProvider:
    def get_subject(self, user: UserProtocol) -> str:
        return f"org:{user.org_id}:dept:{user.dept_id}:user:{user.id}"
```

### 2. RoleProvider

Resolves user roles and handles role-based authorization.

```python
from fastapi_role.protocols import RoleProvider

class RoleProvider(Protocol):
    @abstractmethod
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        """Get all roles for a user."""
        ...
        
    @abstractmethod
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        """Check if user has specific role."""
        ...
```

#### Default Implementation

```python
class DefaultRoleProvider:
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
```

#### Custom Implementations

```python
# Database-backed roles
class DatabaseRoleProvider:
    def __init__(self, db_session, superadmin_role: str = "admin"):
        self.db = db_session
        self.superadmin_role = superadmin_role
        
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        # Query user roles from database
        user_roles = await self.db.execute(
            select(UserRole.role_name)
            .where(UserRole.user_id == user.id)
        )
        return [role[0] for role in user_roles.fetchall()]
        
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        roles = await self.get_user_roles(user)
        return role_name in roles or self.superadmin_role in roles

# Multi-role provider (user can have multiple roles)
class MultiRoleProvider:
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        # User has multiple roles
        return getattr(user, 'roles', [])
        
    async def has_role(self, user: UserProtocol, role_name: str) -> bool:
        user_roles = await self.get_user_roles(user)
        return role_name in user_roles

# Time-based role provider
class TimeBasedRoleProvider:
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        base_roles = [user.role]
        
        # Add time-based roles
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            base_roles.append("business_hours_user")
        else:
            base_roles.append("after_hours_user")
            
        return base_roles

# External service role provider
class ExternalRoleProvider:
    def __init__(self, auth_service_url: str):
        self.auth_service = auth_service_url
        
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        # Query external authentication service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.auth_service}/users/{user.id}/roles"
            )
            return response.json().get("roles", [])
```

### 3. OwnershipProvider

Handles resource ownership validation for different resource types.

```python
from fastapi_role.protocols import OwnershipProvider

class OwnershipProvider(Protocol):
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

#### Default Implementation

```python
class DefaultOwnershipProvider:
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

#### Custom Implementations

```python
# Database-backed ownership
class DatabaseOwnershipProvider:
    def __init__(self, db_session):
        self.db = db_session
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "project":
            project = await self.db.get(Project, resource_id)
            return project and project.owner_id == user.id
            
        elif resource_type == "document":
            document = await self.db.get(Document, resource_id)
            return document and document.author_id == user.id
            
        elif resource_type == "team":
            team = await self.db.get(Team, resource_id)
            return team and (
                team.leader_id == user.id or 
                user.id in team.member_ids
            )
            
        return False

# Multi-tenant ownership
class TenantOwnershipProvider:
    def __init__(self, db_session):
        self.db = db_session
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        # In multi-tenant apps, ownership = same tenant
        resource_table = self._get_resource_table(resource_type)
        if not resource_table:
            return False
            
        resource = await self.db.get(resource_table, resource_id)
        return resource and resource.tenant_id == user.tenant_id
        
    def _get_resource_table(self, resource_type: str):
        mapping = {
            "project": Project,
            "document": Document,
            "user": User,
        }
        return mapping.get(resource_type)

# Hierarchical ownership (teams, departments, organizations)
class HierarchicalOwnershipProvider:
    def __init__(self, db_session):
        self.db = db_session
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "project":
            return await self._check_project_ownership(user, resource_id)
        elif resource_type == "department":
            return await self._check_department_ownership(user, resource_id)
        return False
        
    async def _check_project_ownership(self, user: UserProtocol, project_id: Any) -> bool:
        project = await self.db.get(Project, project_id)
        if not project:
            return False
            
        # Direct ownership
        if project.owner_id == user.id:
            return True
            
        # Team ownership
        if user.team_id and project.team_id == user.team_id:
            return True
            
        # Department ownership (if user is dept manager)
        if (user.role == "department_manager" and 
            project.department_id == user.department_id):
            return True
            
        return False

# File system ownership
class FileSystemOwnershipProvider:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "file":
            file_path = self.base_path / str(resource_id)
            if file_path.exists():
                # Check file ownership (Unix systems)
                stat = file_path.stat()
                return stat.st_uid == user.system_uid
        return False

# API-based ownership
class APIOwnershipProvider:
    def __init__(self, ownership_service_url: str):
        self.service_url = ownership_service_url
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.service_url}/ownership",
                params={
                    "user_id": user.id,
                    "resource_type": resource_type,
                    "resource_id": resource_id
                }
            )
            return response.json().get("owns", False)
```

### 4. PolicyProvider

Manages policy storage and loading for Casbin.

```python
from fastapi_role.protocols import PolicyProvider

class PolicyProvider(Protocol):
    @abstractmethod
    async def load_policies(self) -> List[List[str]]:
        """Load policy rules."""
        ...
        
    @abstractmethod
    async def save_policy(self, policy: List[str]) -> bool:
        """Save a policy rule."""
        ...
        
    @abstractmethod
    async def remove_policy(self, policy: List[str]) -> bool:
        """Remove a policy rule."""
        ...
```

#### Custom Implementations

```python
# Database policy provider
class DatabasePolicyProvider:
    def __init__(self, db_session):
        self.db = db_session
        
    async def load_policies(self) -> List[List[str]]:
        policies = await self.db.execute(select(PolicyRule))
        return [
            [p.subject, p.object, p.action] 
            for p in policies.scalars().all()
        ]
        
    async def save_policy(self, policy: List[str]) -> bool:
        policy_rule = PolicyRule(
            subject=policy[0],
            object=policy[1], 
            action=policy[2]
        )
        self.db.add(policy_rule)
        await self.db.commit()
        return True
        
    async def remove_policy(self, policy: List[str]) -> bool:
        await self.db.execute(
            delete(PolicyRule).where(
                PolicyRule.subject == policy[0],
                PolicyRule.object == policy[1],
                PolicyRule.action == policy[2]
            )
        )
        await self.db.commit()
        return True

# Redis policy provider
class RedisPolicyProvider:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.policy_key = "rbac:policies"
        
    async def load_policies(self) -> List[List[str]]:
        policies = await self.redis.lrange(self.policy_key, 0, -1)
        return [json.loads(policy) for policy in policies]
        
    async def save_policy(self, policy: List[str]) -> bool:
        await self.redis.lpush(self.policy_key, json.dumps(policy))
        return True
        
    async def remove_policy(self, policy: List[str]) -> bool:
        await self.redis.lrem(self.policy_key, 1, json.dumps(policy))
        return True

# File-based policy provider
class FilePolicyProvider:
    def __init__(self, policy_file: str):
        self.policy_file = Path(policy_file)
        
    async def load_policies(self) -> List[List[str]]:
        if not self.policy_file.exists():
            return []
            
        policies = []
        with open(self.policy_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    policies.append(row[:3])
        return policies
        
    async def save_policy(self, policy: List[str]) -> bool:
        with open(self.policy_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(policy)
        return True
        
    async def remove_policy(self, policy: List[str]) -> bool:
        # Read all policies
        policies = await self.load_policies()
        
        # Remove the specified policy
        policies = [p for p in policies if p != policy]
        
        # Write back
        with open(self.policy_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(policies)
        return True
```

### 5. CacheProvider

Provides caching for authorization results to improve performance.

```python
from fastapi_role.protocols import CacheProvider

class CacheProvider(Protocol):
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
        
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        ...
```

#### Custom Implementations

```python
# Redis cache provider
class RedisCacheProvider:
    def __init__(self, redis_client, key_prefix: str = "rbac:"):
        self.redis = redis_client
        self.prefix = key_prefix
        
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(f"{self.prefix}{key}")
        return json.loads(value) if value else None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self.redis.set(
            f"{self.prefix}{key}", 
            json.dumps(value), 
            ex=ttl
        )
        
    async def clear(self, pattern: Optional[str] = None) -> None:
        if pattern:
            keys = await self.redis.keys(f"{self.prefix}{pattern}")
        else:
            keys = await self.redis.keys(f"{self.prefix}*")
            
        if keys:
            await self.redis.delete(*keys)
            
    async def get_stats(self) -> Dict[str, Any]:
        info = await self.redis.info("memory")
        return {
            "memory_used": info.get("used_memory_human"),
            "keys": await self.redis.dbsize()
        }

# In-memory cache provider
class MemoryCacheProvider:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        
    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check TTL
            if key in self.timestamps:
                ttl, timestamp = self.timestamps[key]
                if time.time() - timestamp > ttl:
                    del self.cache[key]
                    del self.timestamps[key]
                    return None
            return self.cache[key]
        return None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # Evict if at max size
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.keys(), 
                           key=lambda k: self.timestamps[k][1])
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
            
        self.cache[key] = value
        if ttl:
            self.timestamps[key] = (ttl, time.time())
            
    async def clear(self, pattern: Optional[str] = None) -> None:
        if pattern:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
                if key in self.timestamps:
                    del self.timestamps[key]
        else:
            self.cache.clear()
            self.timestamps.clear()
            
    async def get_stats(self) -> Dict[str, Any]:
        return {
            "keys": len(self.cache),
            "max_size": self.max_size,
            "memory_usage": sys.getsizeof(self.cache)
        }

# Multi-tier cache provider
class MultiTierCacheProvider:
    def __init__(self, l1_cache: CacheProvider, l2_cache: CacheProvider):
        self.l1 = l1_cache  # Fast cache (memory)
        self.l2 = l2_cache  # Slower cache (Redis)
        
    async def get(self, key: str) -> Optional[Any]:
        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            return value
            
        # Try L2
        value = await self.l2.get(key)
        if value is not None:
            # Promote to L1
            await self.l1.set(key, value, ttl=300)
            return value
            
        return None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # Set in both tiers
        await self.l1.set(key, value, ttl=min(ttl or 300, 300))
        await self.l2.set(key, value, ttl=ttl)
```

## 🔧 Provider Registration

### Single Provider Registration

```python
from fastapi_role import RBACService

# Create custom providers
subject_provider = TenantSubjectProvider()
role_provider = DatabaseRoleProvider(db_session)
cache_provider = RedisCacheProvider(redis_client)

# Register with RBAC service
rbac = RBACService(
    subject_provider=subject_provider,
    role_provider=role_provider,
    cache_provider=cache_provider
)

# Register ownership providers for specific resource types
rbac.register_ownership_provider("project", ProjectOwnershipProvider(db_session))
rbac.register_ownership_provider("document", DocumentOwnershipProvider(db_session))
rbac.register_ownership_provider("team", TeamOwnershipProvider(db_session))
```

### Configuration-Based Registration

```python
from fastapi_role import CasbinConfig

config = CasbinConfig(
    subject_provider=TenantSubjectProvider(),
    role_provider=DatabaseRoleProvider(db_session),
    cache_provider=RedisCacheProvider(redis_client),
    ownership_providers={
        "project": ProjectOwnershipProvider(db_session),
        "document": DocumentOwnershipProvider(db_session),
        "team": TeamOwnershipProvider(db_session),
    }
)

rbac = RBACService(config=config)
```

### Factory Pattern Registration

```python
class ProviderFactory:
    @staticmethod
    def create_providers(config: Dict[str, Any]) -> Dict[str, Any]:
        providers = {}
        
        # Subject provider
        if config.get("multi_tenant"):
            providers["subject_provider"] = TenantSubjectProvider()
        else:
            providers["subject_provider"] = DefaultSubjectProvider()
            
        # Role provider
        if config.get("database_roles"):
            providers["role_provider"] = DatabaseRoleProvider(config["db_session"])
        else:
            providers["role_provider"] = DefaultRoleProvider()
            
        # Cache provider
        if config.get("redis_cache"):
            providers["cache_provider"] = RedisCacheProvider(config["redis_client"])
        else:
            providers["cache_provider"] = MemoryCacheProvider()
            
        return providers

# Usage
config = {
    "multi_tenant": True,
    "database_roles": True,
    "redis_cache": True,
    "db_session": db_session,
    "redis_client": redis_client
}

providers = ProviderFactory.create_providers(config)
rbac = RBACService(**providers)
```

## 🧪 Testing Providers

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def ownership_provider(mock_db):
    return DatabaseOwnershipProvider(mock_db)

async def test_project_ownership(ownership_provider, mock_db):
    # Setup
    user = User(id=1, role="user")
    project = Project(id=123, owner_id=1)
    mock_db.get.return_value = project
    
    # Test
    result = await ownership_provider.check_ownership(user, "project", 123)
    
    # Assert
    assert result is True
    mock_db.get.assert_called_once_with(Project, 123)

async def test_project_not_owned(ownership_provider, mock_db):
    # Setup
    user = User(id=1, role="user")
    project = Project(id=123, owner_id=2)  # Different owner
    mock_db.get.return_value = project
    
    # Test
    result = await ownership_provider.check_ownership(user, "project", 123)
    
    # Assert
    assert result is False
```

### Integration Testing

```python
async def test_provider_integration():
    # Setup real providers
    rbac = RBACService(
        subject_provider=TenantSubjectProvider(),
        role_provider=DatabaseRoleProvider(db_session),
        cache_provider=MemoryCacheProvider()
    )
    
    rbac.register_ownership_provider("project", ProjectOwnershipProvider(db_session))
    
    # Create test data
    user = User(id=1, tenant_id=1, role="manager")
    project = Project(id=123, owner_id=1, tenant_id=1)
    
    # Test end-to-end
    can_access = await rbac.can_access(
        user, 
        ResourceRef("project", 123), 
        "read"
    )
    
    assert can_access is True
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    user_id=st.integers(min_value=1),
    tenant_id=st.integers(min_value=1),
    resource_id=st.integers(min_value=1)
)
async def test_tenant_ownership_property(user_id, tenant_id, resource_id):
    """For any user and resource in the same tenant, ownership should be True"""
    
    provider = TenantOwnershipProvider(mock_db)
    user = User(id=user_id, tenant_id=tenant_id)
    
    # Mock resource with same tenant
    mock_resource = MockResource(id=resource_id, tenant_id=tenant_id)
    mock_db.get.return_value = mock_resource
    
    result = await provider.check_ownership(user, "resource", resource_id)
    assert result is True
```

## 🚀 Best Practices

### 1. Provider Composition

```python
# Combine multiple providers for complex logic
class CompositeOwnershipProvider:
    def __init__(self, providers: List[OwnershipProvider]):
        self.providers = providers
        
    async def check_ownership(self, user, resource_type, resource_id):
        # Try each provider until one returns True
        for provider in self.providers:
            if await provider.check_ownership(user, resource_type, resource_id):
                return True
        return False

# Usage
composite_provider = CompositeOwnershipProvider([
    DirectOwnershipProvider(),
    TeamOwnershipProvider(),
    DepartmentOwnershipProvider()
])
```

### 2. Provider Caching

```python
class CachedOwnershipProvider:
    def __init__(self, base_provider: OwnershipProvider, cache: CacheProvider):
        self.base_provider = base_provider
        self.cache = cache
        
    async def check_ownership(self, user, resource_type, resource_id):
        cache_key = f"ownership:{user.id}:{resource_type}:{resource_id}"
        
        # Check cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        # Call base provider
        result = await self.base_provider.check_ownership(user, resource_type, resource_id)
        
        # Cache result
        await self.cache.set(cache_key, result, ttl=300)
        
        return result
```

### 3. Provider Validation

```python
def validate_provider(provider: Any, protocol: type) -> bool:
    """Validate that provider implements required protocol"""
    required_methods = [
        method for method in dir(protocol)
        if not method.startswith('_') and callable(getattr(protocol, method))
    ]
    
    for method in required_methods:
        if not hasattr(provider, method):
            raise ValueError(f"Provider missing required method: {method}")
        if not callable(getattr(provider, method)):
            raise ValueError(f"Provider method not callable: {method}")
            
    return True

# Usage
validate_provider(my_ownership_provider, OwnershipProvider)
```

### 4. Provider Error Handling

```python
class RobustOwnershipProvider:
    def __init__(self, base_provider: OwnershipProvider, fallback_allow: bool = False):
        self.base_provider = base_provider
        self.fallback_allow = fallback_allow
        
    async def check_ownership(self, user, resource_type, resource_id):
        try:
            return await self.base_provider.check_ownership(user, resource_type, resource_id)
        except Exception as e:
            # Log error
            logger.error(f"Ownership check failed: {e}")
            
            # Return safe fallback
            return self.fallback_allow
```

## 🎯 Key Takeaways

1. **Pure Separation**: Providers keep business logic out of the RBAC core
2. **Pluggable Architecture**: Swap providers without changing RBAC code
3. **Protocol-Based**: Clear contracts ensure compatibility
4. **Composable**: Combine providers for complex scenarios
5. **Testable**: Easy to unit test and mock providers
6. **Flexible**: Support any business domain or integration pattern

The provider architecture is what makes fastapi-role a truly pure general RBAC engine. By implementing custom providers, you can integrate with any system while keeping the core RBAC logic business-agnostic.