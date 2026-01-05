# Configuration Reference

`fastapi-role` offers a hierarchical configuration system. You can configure it via:

1.  **Defaults**: Zero-config needed for basic usage.
2.  **Files**: YAML/JSON/Python configuration files.
3.  **Environment Variables**: Override settings for deployment.
4.  **Code**: Direct programmatic configuration.

## CasbinConfig

The core configuration object is `CasbinConfig`.

```python
from fastapi_role.core.config import CasbinConfig

config = CasbinConfig(
    app_name="my_app",
    filepath="/path/to/config/dir",
    auto_save=True
)
```

### Parameters

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `app_name` | `str` | `"fastapi-role"` | Used to generate default config paths in user data directory. |
| `filepath` | `str` | `None` | Custom directory for Casbin model/policy files. If None, uses platform-specific user data dir. |
| `model_path` | `str` | `None` | Explicit path to `rbac_model.conf`. |
| `policy_path` | `str` | `None` | Explicit path to `rbac_policy.csv`. |
| `auto_save` | `bool` | `True` | Whether to auto-save policy changes back to the CSV/adapter. |

## File Configuration

By default, the library looks for `rbac_model.conf` and `rbac_policy.csv` in the configured `filepath` (or default app data directory).

### rbac_model.conf

Defines the Casbin model. The default model supports RBAC with domains/tenants.

```ini
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
```

### rbac_policy.csv

Defines your initial roles and permissions.

```csv
p, admin, *, *
p, user, profile, read
g, alice@example.com, admin
```

## Runtime Configuration via Providers

For advanced customization, you inject **Providers** into `RBACService`.

```python
service = RBACService(
    db=session,
    subject_provider=MySubjectProvider(),
    role_provider=MyRoleProvider(),
    cache_provider=RedisCacheProvider()
)
```

### Subject Provider
Determines what is used as the `sub` (subject) in Casbin queries.
*   **Default**: Uses `user.email`.
*   **Custom**: Create a class implementing `SubjectProvider` protocol.

### Role Provider
Determines how to extract roles from a user object.
*   **Default**: Uses `user.role`.
*   **Custom**: Implement `RoleProvider` protocol (e.g., to fetch roles from a DB).

### Ownership Provider
Handling resource ownership (e.g., "User can only edit their own profile").
*   **Default**: Superadmins can access everything.
*   **Custom**: Register providers via `OwnershipRegistry`.

```python
class QuoteOwnershipProvider:
    async def check_ownership(self, user, resource_type, resource_id):
        # queries DB to check if user owns quote
        return True

# Registering
registry = OwnershipRegistry()
registry.register("quote", QuoteOwnershipProvider())
```

### Cache Provider
Controls permission result caching.
*   **Default**: In-memory dictionary with TTL.
*   **Custom**: Implement `CacheProvider` (e.g., for Redis).

## Environment Variables

(Note: Environment variable support is planned for future versions to override specific config keys automatically.)
