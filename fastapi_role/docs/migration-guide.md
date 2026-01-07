# Migration Guide: From Business-Coupled to Pure General RBAC

This guide helps you migrate from business-coupled RBAC systems to fastapi-role's pure general RBAC engine.

## 🎯 Migration Philosophy

The migration transforms your RBAC system from:

- ❌ **Business-Coupled**: Hardcoded roles, entity-specific methods, business assumptions
- ✅ **Pure General RBAC**: Dynamic roles, resource-agnostic methods, zero business assumptions

## 📋 Pre-Migration Checklist

Before starting migration, assess your current system:

### 1. Identify Business Coupling

Look for these patterns in your current code:

```python
# ❌ Business-coupled patterns to replace:

# Hardcoded business roles
class Role(Enum):
    SUPERADMIN = "superadmin"
    SALESMAN = "salesman" 
    CUSTOMER = "customer"

# Entity-specific access methods
def get_accessible_customers(user): pass
def get_accessible_orders(user): pass
def check_customer_ownership(user, customer_id): pass

# Business model imports in RBAC code
from app.models.customer import Customer
from app.models.order import Order

# Hardcoded business logic
if user.role == "salesman" and customer.region == user.region:
    return True
```

### 2. Inventory Current Features

Document what your current RBAC system does:

- [ ] Role definitions and hierarchy
- [ ] Permission checking mechanisms
- [ ] Ownership validation logic
- [ ] Caching strategies
- [ ] Integration points with your application
- [ ] Custom business rules

### 3. Plan Resource Mapping

Map your business entities to generic resource types:

| Current Business Entity | Generic Resource Type |
|------------------------|----------------------|
| Customer | `customer` |
| Order | `order` |
| Product | `product` |
| Invoice | `invoice` |
| User | `user` |

## 🚀 Step-by-Step Migration

### Step 1: Install fastapi-role

```bash
# Remove old RBAC dependencies
pip uninstall old-rbac-library

# Install fastapi-role
pip install fastapi-role[all]
```

### Step 2: Replace Hardcoded Roles

#### Before (Business-Coupled)
```python
# old_rbac.py
class Role(Enum):
    SUPERADMIN = "superadmin"
    SALESMAN = "salesman"
    CUSTOMER = "customer"
    MANAGER = "manager"

@require_role(Role.SALESMAN)
def get_customer_data(customer_id: int):
    pass
```

#### After (Pure General RBAC)
```python
# new_rbac.py
from fastapi_role import create_roles, require, Permission

# Create dynamic roles from your existing role names
Role = create_roles(
    ["superadmin", "salesman", "customer", "manager"], 
    superadmin="superadmin"
)

@require(Role.SALESMAN, Permission("customer", "read"))
async def get_customer_data(customer_id: int, current_user: User, rbac: RBACService):
    pass
```

### Step 3: Replace Entity-Specific Methods

#### Before (Business-Coupled)
```python
# old_rbac_service.py
class OldRBACService:
    def get_accessible_customers(self, user: User) -> List[int]:
        if user.role == "superadmin":
            return self.db.query(Customer).all()
        elif user.role == "salesman":
            return self.db.query(Customer).filter_by(region=user.region).all()
        return []
        
    def check_customer_ownership(self, user: User, customer_id: int) -> bool:
        if user.role == "superadmin":
            return True
        customer = self.db.get(Customer, customer_id)
        return customer and customer.salesman_id == user.id
```

#### After (Pure General RBAC)
```python
# new_rbac_service.py
from fastapi_role import RBACService, ResourceRef
from fastapi_role.protocols import OwnershipProvider

class CustomerOwnershipProvider(OwnershipProvider):
    def __init__(self, db_session):
        self.db = db_session
        
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "customer":
            customer = await self.db.get(Customer, resource_id)
            return customer and customer.salesman_id == user.id
        return False

# Setup
rbac = RBACService()
rbac.register_ownership_provider("customer", CustomerOwnershipProvider(db_session))

# Usage - now resource-agnostic!
async def get_accessible_resources(user: User, resource_type: str) -> List[Any]:
    # Use generic resource access
    permissions = await rbac.resolve_permissions(user)
    if resource_type in permissions and "read" in permissions[resource_type]:
        # Apply ownership filtering
        return await filter_by_ownership(user, resource_type)
    return []

async def check_resource_access(user: User, resource_type: str, resource_id: Any) -> bool:
    resource = ResourceRef(resource_type, resource_id)
    return await rbac.can_access(user, resource, "read")
```

### Step 4: Update Decorators

#### Before (Business-Coupled)
```python
# old_decorators.py
@require_role("salesman")
@require_customer_access
def update_customer(customer_id: int):
    pass

@require_role("manager") 
@require_order_ownership
def approve_order(order_id: int):
    pass
```

#### After (Pure General RBAC)
```python
# new_decorators.py
from fastapi_role import require, Permission

@require(Role.SALESMAN, Permission("customer", "update"))
async def update_customer(customer_id: int, current_user: User, rbac: RBACService):
    # Business logic here
    pass

@require(Role.MANAGER, Permission("order", "approve"))
async def approve_order(order_id: int, current_user: User, rbac: RBACService):
    # Business logic here
    pass
```

### Step 5: Migrate Custom Business Logic

#### Before (Business-Coupled)
```python
# old_business_logic.py
def can_access_customer(user: User, customer: Customer) -> bool:
    if user.role == "superadmin":
        return True
    elif user.role == "salesman":
        return customer.region == user.region
    elif user.role == "customer":
        return customer.id == user.customer_id
    return False
```

#### After (Pure General RBAC)
```python
# new_business_logic.py - implement as ownership provider
class RegionalOwnershipProvider(OwnershipProvider):
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "customer":
            customer = await self.db.get(Customer, resource_id)
            if not customer:
                return False
                
            # Superadmin bypass (handled by RBACService automatically)
            # Business logic: regional access for salesmen
            if user.role == "salesman":
                return customer.region == user.region
            # Business logic: customers can access their own record
            elif user.role == "customer":
                return customer.id == user.customer_id
                
        return False

# Register the provider
rbac.register_ownership_provider("customer", RegionalOwnershipProvider())
```

### Step 6: Update Framework Integration

#### Before (FastAPI Business-Coupled)
```python
# old_fastapi.py
from old_rbac import require_role, RBACService

rbac = RBACService()  # Global instance

@app.get("/customers/{customer_id}")
@require_role("salesman")
def get_customer(customer_id: int, current_user: User = Depends(get_current_user)):
    if not rbac.check_customer_ownership(current_user, customer_id):
        raise HTTPException(403, "Access denied")
    return get_customer_data(customer_id)
```

#### After (Pure General RBAC)
```python
# new_fastapi.py
from fastapi_role import RBACService, require, Permission

rbac = RBACService()

# Business function (framework-agnostic)
@require(Role.SALESMAN, Permission("customer", "read"))
async def get_customer_business(customer_id: int, current_user: User, rbac: RBACService):
    # Business logic here - works with any framework
    return {"id": customer_id, "name": "Customer Name"}

# FastAPI endpoint (thin wrapper)
@app.get("/customers/{customer_id}")
async def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(lambda: rbac)
):
    return await get_customer_business(customer_id, current_user, rbac_service)
```

## 🔧 Advanced Migration Scenarios

### Scenario 1: Complex Role Hierarchies

#### Before (Hardcoded Hierarchy)
```python
class Role(Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    SALESMAN = "salesman"
    CUSTOMER = "customer"

def has_admin_access(user: User) -> bool:
    return user.role in ["superadmin", "admin", "manager"]
```

#### After (Policy-Driven Hierarchy)
```python
# Create roles
Role = create_roles(
    ["superadmin", "admin", "manager", "salesman", "customer"],
    superadmin="superadmin"
)

# Define hierarchy in Casbin policy
# policies.csv:
# g, admin, manager
# g, manager, salesman
# p, manager, *, read
# p, admin, *, write
# p, superadmin, *, *

config = CasbinConfig(policy_path="policies.csv")
rbac = RBACService(config=config)
```

### Scenario 2: Multi-Tenant Systems

#### Before (Hardcoded Tenant Logic)
```python
def check_tenant_access(user: User, resource: Any) -> bool:
    return user.tenant_id == resource.tenant_id
```

#### After (Provider-Based Multi-Tenancy)
```python
class TenantOwnershipProvider(OwnershipProvider):
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        # Get resource from database
        resource_class = self._get_resource_class(resource_type)
        resource = await self.db.get(resource_class, resource_id)
        
        # Check tenant ownership
        return resource and resource.tenant_id == user.tenant_id
        
    def _get_resource_class(self, resource_type: str):
        mapping = {
            "customer": Customer,
            "order": Order,
            "product": Product,
        }
        return mapping.get(resource_type)

# Also use tenant-aware subject provider
class TenantSubjectProvider(SubjectProvider):
    def get_subject(self, user: UserProtocol) -> str:
        return f"user:{user.id}:tenant:{user.tenant_id}"

rbac = RBACService(subject_provider=TenantSubjectProvider())
rbac.register_ownership_provider("*", TenantOwnershipProvider(db_session))
```

### Scenario 3: Time-Based Access

#### Before (Hardcoded Time Logic)
```python
def check_business_hours_access(user: User) -> bool:
    if user.role == "admin":
        return True  # Admins always have access
    
    current_hour = datetime.now().hour
    return 9 <= current_hour <= 17  # Business hours only
```

#### After (Provider-Based Time Logic)
```python
class TimeBasedRoleProvider(RoleProvider):
    def __init__(self, base_provider: RoleProvider):
        self.base_provider = base_provider
        
    async def get_user_roles(self, user: UserProtocol) -> List[str]:
        base_roles = await self.base_provider.get_user_roles(user)
        
        # Add time-based roles
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:
            base_roles.append("business_hours_user")
        else:
            base_roles.append("after_hours_user")
            
        return base_roles

# Use in policies
# p, business_hours_user, order, create
# p, after_hours_user, order, read
# p, admin, *, *

rbac = RBACService(role_provider=TimeBasedRoleProvider(DefaultRoleProvider()))
```

## 🧪 Testing Migration

### 1. Parallel Testing

Run both old and new systems in parallel:

```python
# test_migration.py
async def test_access_parity():
    """Ensure new RBAC gives same results as old RBAC"""
    
    test_cases = [
        (salesman_user, "customer", 123, "read"),
        (admin_user, "order", 456, "write"),
        (customer_user, "customer", 789, "read"),
    ]
    
    for user, resource_type, resource_id, action in test_cases:
        # Old system result
        old_result = old_rbac.check_access(user, resource_type, resource_id, action)
        
        # New system result
        resource = ResourceRef(resource_type, resource_id)
        new_result = await new_rbac.can_access(user, resource, action)
        
        assert old_result == new_result, f"Mismatch for {user.id}, {resource_type}:{resource_id}, {action}"
```

### 2. Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    user_role=st.sampled_from(["admin", "salesman", "customer"]),
    resource_type=st.sampled_from(["customer", "order", "product"]),
    action=st.sampled_from(["read", "write", "delete"])
)
async def test_rbac_consistency(user_role, resource_type, action):
    """Test that RBAC behavior is consistent across different inputs"""
    
    user = User(id=1, role=user_role)
    resource = ResourceRef(resource_type, 123)
    
    # Should not raise exceptions
    result = await rbac.can_access(user, resource, action)
    assert isinstance(result, bool)
```

### 3. Performance Testing

```python
import time

async def test_performance_comparison():
    """Compare performance of old vs new RBAC"""
    
    users = [User(id=i, role="salesman") for i in range(100)]
    
    # Test old system
    start = time.time()
    for user in users:
        old_rbac.get_accessible_customers(user)
    old_time = time.time() - start
    
    # Test new system
    start = time.time()
    for user in users:
        await rbac.resolve_permissions(user)
    new_time = time.time() - start
    
    print(f"Old system: {old_time:.3f}s")
    print(f"New system: {new_time:.3f}s")
    
    # New system should be comparable or faster
    assert new_time <= old_time * 1.5  # Allow 50% slower at most
```

## 🚨 Common Migration Pitfalls

### 1. Forgetting Async/Await

```python
# ❌ Wrong - forgetting async/await
@require(Role.ADMIN)
def admin_function(user: User, rbac: RBACService):
    return rbac.can_access(user, resource, "read")  # Missing await!

# ✅ Correct - proper async/await
@require(Role.ADMIN)
async def admin_function(user: User, rbac: RBACService):
    return await rbac.can_access(user, resource, "read")
```

### 2. Not Updating Function Signatures

```python
# ❌ Wrong - old function signature
@require(Role.ADMIN)
def admin_function():
    pass

# ✅ Correct - new function signature with user and rbac
@require(Role.ADMIN)
async def admin_function(current_user: User, rbac: RBACService):
    pass
```

### 3. Hardcoding Resource Types

```python
# ❌ Wrong - still hardcoding business concepts
@require(Permission("customer", "read"))
async def get_customer_orders(customer_id: int, user: User, rbac: RBACService):
    # Still thinking in business terms
    pass

# ✅ Correct - generic resource thinking
@require(Permission("order", "read"))
async def get_orders_by_owner(owner_id: int, owner_type: str, user: User, rbac: RBACService):
    # Generic resource approach
    pass
```

### 4. Not Implementing Ownership Providers

```python
# ❌ Wrong - no ownership logic
rbac = RBACService()  # No ownership providers registered

# ✅ Correct - implement ownership providers
rbac = RBACService()
rbac.register_ownership_provider("customer", CustomerOwnershipProvider())
rbac.register_ownership_provider("order", OrderOwnershipProvider())
```

## 📊 Migration Checklist

### Pre-Migration
- [ ] Audit current RBAC system for business coupling
- [ ] Document existing roles and permissions
- [ ] Map business entities to generic resource types
- [ ] Plan provider implementations
- [ ] Set up parallel testing environment

### During Migration
- [ ] Replace hardcoded roles with dynamic roles
- [ ] Convert entity-specific methods to resource-agnostic methods
- [ ] Implement ownership providers for each resource type
- [ ] Update decorators to use new syntax
- [ ] Add async/await to all RBAC-protected functions
- [ ] Update function signatures to include user and rbac parameters

### Post-Migration
- [ ] Run parallel tests to ensure parity
- [ ] Performance test the new system
- [ ] Update documentation and examples
- [ ] Train team on new patterns
- [ ] Remove old RBAC code
- [ ] Monitor production for issues

### Validation
- [ ] All tests pass
- [ ] Performance is acceptable
- [ ] No business coupling remains
- [ ] System works with arbitrary resource types
- [ ] Providers handle all custom business logic
- [ ] Framework integration works correctly

## 🎯 Success Criteria

Your migration is successful when:

1. ✅ **Zero Business Coupling**: No hardcoded business concepts in RBAC core
2. ✅ **Resource Agnostic**: System works with any resource type
3. ✅ **Framework Independent**: Same business functions work with any framework
4. ✅ **Provider-Based**: All business logic in pluggable providers
5. ✅ **Configuration-Driven**: Behavior defined by data, not code
6. ✅ **Test Parity**: New system produces same results as old system
7. ✅ **Performance**: New system performs as well or better than old system

## 🚀 Next Steps

After successful migration:

1. **Optimize**: Fine-tune providers and caching for your use case
2. **Extend**: Add new resource types without changing RBAC code
3. **Scale**: Use the pure general RBAC in other applications
4. **Contribute**: Share your provider implementations with the community

Congratulations! You now have a pure general RBAC system that will work with any business domain. 🎉