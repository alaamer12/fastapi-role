# fastapi-role System Behavior Guide

This document explains the behavior of the fastapi-role library, including how the provider architecture works, default behaviors, and important concepts that users need to understand.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Provider Architecture](#provider-architecture)
3. [Default Behaviors](#default-behaviors)
4. [Authorization Flow](#authorization-flow)
5. [Caching Behavior](#caching-behavior)
6. [Ownership Validation](#ownership-validation)
7. [Common Scenarios](#common-scenarios)
8. [Security Considerations](#security-considerations)

---

## Core Concepts

### What is a Provider?

A **provider** is a pluggable component that handles a specific aspect of the RBAC system. fastapi-role uses providers to make the library flexible and customizable without requiring you to modify core code.

**Available Providers:**
- **SubjectProvider**: Determines what identifier to use for a user in Casbin policies
- **RoleProvider**: Determines how to extract and validate user roles
- **CacheProvider**: Handles caching of permission check results
- **OwnershipProvider**: Validates resource ownership for specific resource types

### Why Providers?

Different applications have different needs:
- Some use email as the user identifier, others use user ID
- Some have a single role per user, others have multiple roles
- Some need Redis caching, others prefer in-memory
- Some have complex ownership rules, others have simple ones

Providers let you customize these behaviors without forking the library.

---

## Provider Architecture

### How Providers Work

When you create an `RBACService`, you can optionally pass custom providers:

```python
from fastapi_role import RBACService
from fastapi_role.providers import DefaultSubjectProvider

# Use custom subject provider
custom_subject = DefaultSubjectProvider(field_name="id")

service = RBACService(
    db,
    config=casbin_config,
    subject_provider=custom_subject  # Custom provider
)
```

If you don't provide a provider, the service uses the **default provider** for that component.

### Provider Initialization Order

1. **User provides providers** (optional)
2. **Service initializes defaults** for any missing providers
3. **Service uses providers** throughout its lifetime

**Important**: Providers are set at service creation and cannot be changed later. If you need different behavior, create a new service instance.

---

## Default Behaviors

### 1. Default Subject Provider

**What it does**: Extracts the Casbin subject identifier from a user object.

**Default behavior**: Returns `user.email`

```python
# Default behavior
user = User(id=1, email="john@example.com", role="customer")
subject = subject_provider.get_subject(user)
# Result: "john@example.com"
```

**Why email?** Email is a common, unique identifier that's human-readable in logs and policies.

**Customization example**:
```python
# Use user ID instead
custom_subject = DefaultSubjectProvider(field_name="id")
subject = custom_subject.get_subject(user)
# Result: "1"
```

---

### 2. Default Role Provider

**What it does**: Extracts user roles and validates role membership.

**Default behavior**: 
- Returns `user.role` as a string
- Superadmin role (`"superadmin"` by default) bypasses all role checks

```python
# Regular user
user = User(id=1, email="john@example.com", role="customer")
role_provider.has_role(user, "customer")  # True
role_provider.has_role(user, "admin")     # False

# Superadmin user
admin = User(id=2, email="admin@example.com", role="superadmin")
role_provider.has_role(admin, "customer")  # True (superadmin bypass)
role_provider.has_role(admin, "admin")     # True (superadmin bypass)
role_provider.has_role(admin, "any_role")  # True (superadmin bypass)
```

**Why superadmin bypass?** Superadmins need access to everything for system administration and debugging.

**Customization example**:
```python
# Use "root" as superadmin role
custom_role = DefaultRoleProvider(superadmin_role="root")
```

---

### 3. Default Cache Provider

**What it does**: Caches permission check results to improve performance.

**Default behavior**:
- In-memory dictionary-based cache
- 5-minute TTL (300 seconds) by default
- Tracks hits, misses, and hit rate
- Automatically expires old entries

```python
# First check - hits Casbin enforcer
result1 = await service.check_permission(user, "orders", "read")
# Casbin enforcer called: YES
# Cached: YES

# Second check - hits cache
result2 = await service.check_permission(user, "orders", "read")
# Casbin enforcer called: NO (cache hit)
# Cached: YES (returns cached result)
```

**Why caching?** Permission checks can be expensive, especially with complex policies. Caching dramatically improves performance.

**Cache statistics**:
```python
stats = service.get_cache_stats()
# {
#     "size": 42,           # Number of cached entries
#     "hits": 150,          # Cache hits
#     "misses": 42,         # Cache misses
#     "hit_rate": 0.78,     # 78% hit rate
#     "customer_cache_size": 5,
#     "cache_age_minutes": 2.5
# }
```

**Customization example**:
```python
# Cache with 10-minute TTL
custom_cache = DefaultCacheProvider(default_ttl=600)

# Or no TTL (cache forever until cleared)
custom_cache = DefaultCacheProvider(default_ttl=None)
```

---

### 4. Default Ownership Provider

**What it does**: Validates whether a user owns or has access to a specific resource.

**Default behavior**:
- **Superadmin users**: Always granted access (bypass)
- **Non-superadmin users**: Denied by default
- **Configurable allowed roles**: Can grant access to specific roles

```python
# Superadmin - always allowed
admin = User(id=1, role="superadmin")
await service.check_resource_ownership(admin, "order", 123)  # True

# Regular user - denied by default
customer = User(id=2, role="customer")
await service.check_resource_ownership(customer, "order", 123)  # False
```

**Why deny by default?** This is a **fail-closed** security approach. It's safer to deny access and require explicit permission than to allow access by default.

**Customization example**:
```python
# Allow specific roles
custom_ownership = DefaultOwnershipProvider(
    superadmin_role="superadmin",
    default_allow=False,
    allowed_roles={"manager", "admin"}
)
```

---

## Authorization Flow

### Permission Check Flow

When you call `check_permission(user, resource, action)`:

```
1. Extract subject from user
   └─> subject_provider.get_subject(user)
   
2. Check cache
   └─> cache_provider.get(cache_key)
   └─> If cached: return cached result
   
3. Evaluate Casbin policy
   └─> enforcer.enforce(subject, resource, action)
   
4. Cache result
   └─> cache_provider.set(cache_key, result)
   
5. Log if denied
   └─> logger.warning("Authorization denied...")
   
6. Return result
```

### Resource Ownership Check Flow

When you call `check_resource_ownership(user, resource_type, resource_id)`:

```
1. Check for specific provider
   └─> ownership_registry.has_provider(resource_type)
   └─> If found: use specific provider
   
2. Check for wildcard provider
   └─> ownership_registry.has_provider("*")
   └─> If found: use wildcard provider
   
3. No provider found
   └─> Return False (fail-closed)
```

**Example**:
```python
# Register custom provider for "order" resources
service.ownership_registry.register("order", CustomOrderOwnershipProvider())

# Check ownership
await service.check_resource_ownership(user, "order", 123)
# Uses CustomOrderOwnershipProvider

await service.check_resource_ownership(user, "invoice", 456)
# No specific provider, falls back to wildcard ("*")
# Uses DefaultOwnershipProvider
```

---

## Caching Behavior

### What Gets Cached?

**Cached**:
- Permission check results (`check_permission`)
- Cache key format: `{user_id}:{resource}:{action}`

**Not Cached**:
- Resource ownership checks (too dynamic)
- Role checks (very fast, no need)
- Privilege evaluations (composite checks)

### Cache Invalidation

**Automatic invalidation**:
- TTL expiration (default 5 minutes)
- Calling `service.clear_cache()`

**When to clear cache**:
```python
# After role assignment
await service.assign_role_to_user(user, Role.ADMIN)
# Cache is automatically cleared

# After policy changes
service.enforcer.add_policy("customer", "orders", "create")
service.clear_cache()  # Manual clear needed

# After user updates
user.role = "admin"
await db.commit()
service.clear_cache()  # Manual clear needed
```

### Cache Expiration Behavior

```python
# Set value with TTL
cache_provider.set("key", True, ttl=60)  # 60 seconds

# After 30 seconds
cache_provider.get("key")  # Returns True

# After 61 seconds
cache_provider.get("key")  # Returns None (expired)
```

**Important**: Expired entries are removed from the cache when accessed, not proactively. This is called "lazy expiration."

---

## Ownership Validation

### Why Ownership Checks Exist

Permission checks answer: "Can this user perform this action?"
Ownership checks answer: "Does this user own this specific resource?"

**Example scenario**:
- User has permission to "read orders"
- But should only read THEIR OWN orders
- Ownership check validates: "Is this order owned by this user?"

### Default Ownership Behavior

**The default ownership provider is registered for ALL resource types** using the wildcard pattern (`"*"`):

```python
# This happens automatically in RBACService.__init__
self.ownership_registry.register(
    "*",  # Wildcard - matches all resource types
    DefaultOwnershipProvider(superadmin_role="superadmin", default_allow=False)
)
```

**What this means**:
- **Superadmin users**: Can access any resource
- **Non-superadmin users**: Denied access to all resources by default

**Why this behavior?**

This is intentional and secure:
1. **Fail-closed security**: Better to deny by default and require explicit permission
2. **Forces custom providers**: You must implement ownership logic for your resources
3. **Prevents accidental data leaks**: Users can't access resources they shouldn't

### Implementing Custom Ownership

**Step 1: Create a custom ownership provider**

```python
class OrderOwnershipProvider:
    """Check if user owns an order."""
    
    def __init__(self, db):
        self.db = db
    
    async def check_ownership(self, user, resource_type, resource_id):
        # Superadmin bypass
        if user.role == "superadmin":
            return True
        
        # Query database
        order = await self.db.get(Order, resource_id)
        if not order:
            return False
        
        # Check if user owns the order
        return order.user_id == user.id
```

**Step 2: Register the provider**

```python
# Register for specific resource type
service.ownership_registry.register(
    "order",
    OrderOwnershipProvider(db)
)
```

**Step 3: Use it**

```python
# Now ownership checks for "order" use your custom provider
can_access = await service.check_resource_ownership(user, "order", 123)

# Other resource types still use the wildcard default
can_access = await service.check_resource_ownership(user, "invoice", 456)
# Uses DefaultOwnershipProvider (denies non-superadmin)
```

---

## Common Scenarios

### Scenario 1: User Can't Access Their Own Resources

**Problem**:
```python
# User tries to access their own order
result = await service.check_resource_ownership(user, "order", 123)
# Result: False (denied)
```

**Cause**: No custom ownership provider registered for "order" resource type.

**Solution**: Register a custom ownership provider:
```python
service.ownership_registry.register("order", CustomOrderOwnershipProvider(db))
```

---

### Scenario 2: Cache Not Updating After Role Change

**Problem**:
```python
# Change user role
user.role = "admin"
await db.commit()

# Permission check still returns old result
result = await service.check_permission(user, "orders", "delete")
# Result: False (cached from before role change)
```

**Cause**: Cache not cleared after role change.

**Solution**: Clear cache after role changes:
```python
user.role = "admin"
await db.commit()
service.clear_cache()  # Clear cache
```

**Better solution**: Use the built-in method:
```python
await service.assign_role_to_user(user, Role.ADMIN)
# Automatically clears cache
```

---

### Scenario 3: Superadmin Can't Access Resources

**Problem**:
```python
admin = User(id=1, role="superadmin")
result = await service.check_resource_ownership(admin, "order", 123)
# Result: False (denied)
```

**Cause**: Custom ownership provider doesn't implement superadmin bypass.

**Solution**: Always check for superadmin in custom providers:
```python
async def check_ownership(self, user, resource_type, resource_id):
    # Always check superadmin first
    if user.role == "superadmin":
        return True
    
    # Then your custom logic
    # ...
```

---

### Scenario 4: Using User ID Instead of Email

**Problem**: Your Casbin policies use user IDs, but the library uses emails by default.

**Solution**: Use a custom subject provider:
```python
from fastapi_role.providers import DefaultSubjectProvider

# Create service with custom subject provider
service = RBACService(
    db,
    config=casbin_config,
    subject_provider=DefaultSubjectProvider(field_name="id")
)

# Now Casbin policies use user.id instead of user.email
```

---

## Security Considerations

### Fail-Closed vs Fail-Open

**Fail-Closed** (Default): Deny access when in doubt
- Default ownership provider denies non-superadmin users
- Permission check errors return `False`
- Missing providers return `False`

**Fail-Open** (Dangerous): Allow access when in doubt
- Not recommended for production
- Only use for development/testing

### Superadmin Bypass

**What it means**: Superadmin role bypasses most checks.

**Where it applies**:
- ✅ Role checks (`has_role`)
- ✅ Ownership checks (default provider)
- ❌ Permission checks (still evaluated by Casbin)

**Why permission checks aren't bypassed**: 
Casbin policies should explicitly grant superadmin access. This provides an audit trail and allows fine-grained control.

**Best practice**:
```python
# In your Casbin policy
config.add_policy(Role.SUPERADMIN, "*", "*", "allow")
```

### Cache Security

**Risks**:
- Stale permissions after role changes
- Cached denials preventing legitimate access
- Memory exhaustion from large caches

**Mitigations**:
- Use TTL (default 5 minutes)
- Clear cache after role/policy changes
- Monitor cache size via `get_cache_stats()`

### Logging

**What gets logged**:
- ✅ Authorization failures (WARNING level)
- ✅ Permission check errors (ERROR level)
- ✅ Role assignments (INFO level)
- ✅ Cache hits (DEBUG level)

**What's NOT logged**:
- ❌ User passwords or sensitive data
- ❌ Full user objects
- ❌ Resource content

**Log format**:
```
WARNING - Authorization denied: user=john@example.com, resource=orders, action=delete, role=customer
```

---

## Best Practices

### 1. Always Implement Custom Ownership Providers

Don't rely on the default ownership provider for production resources:

```python
# ❌ Bad - relies on default (denies all non-superadmin)
result = await service.check_resource_ownership(user, "order", 123)

# ✅ Good - custom provider with business logic
service.ownership_registry.register("order", OrderOwnershipProvider(db))
result = await service.check_resource_ownership(user, "order", 123)
```

### 2. Clear Cache After Policy Changes

```python
# ✅ Good
service.enforcer.add_policy("customer", "orders", "create")
service.clear_cache()
```

### 3. Use Built-in Methods When Available

```python
# ❌ Bad - manual role change
user.role = "admin"
await db.commit()
service.clear_cache()

# ✅ Good - built-in method
await service.assign_role_to_user(user, Role.ADMIN)
```

### 4. Monitor Cache Performance

```python
# Periodically check cache stats
stats = service.get_cache_stats()
if stats["hit_rate"] < 0.5:
    logger.warning(f"Low cache hit rate: {stats['hit_rate']:.2%}")
```

### 5. Use Appropriate TTL

```python
# ✅ Good - reasonable TTL for security-sensitive data
cache_provider = DefaultCacheProvider(default_ttl=300)  # 5 minutes

# ⚠️ Risky - very long TTL
cache_provider = DefaultCacheProvider(default_ttl=3600)  # 1 hour

# ❌ Dangerous - no expiration
cache_provider = DefaultCacheProvider(default_ttl=None)  # Never expires
```

---

## Summary

**Key Takeaways**:

1. **Providers are pluggable**: Customize behavior without modifying core code
2. **Defaults are secure**: Fail-closed, superadmin bypass, reasonable TTL
3. **Ownership requires custom logic**: Default provider denies non-superadmin
4. **Cache improves performance**: But must be cleared after changes
5. **Superadmin bypasses most checks**: Except Casbin permission evaluation
6. **Always check superadmin first**: In custom ownership providers
7. **Monitor and log**: Use stats and logs to understand system behavior

**Next Steps**:
- Read the [API Documentation](API.md) for detailed method signatures
- Check [Examples](examples/) for common use cases
- Review [Migration Guide](MIGRATION.md) if upgrading from older versions
