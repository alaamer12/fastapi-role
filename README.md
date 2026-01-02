# FastAPI-Role

A powerful and flexible Role-Based Access Control (RBAC) library for FastAPI applications, powered by Casbin.

## Features

- **Dynamic Role Creation**: Define roles at runtime using a factory pattern.
- **Role Composition**: Combine roles using bitwise OR (`|`).
- **Code-First Configuration**: Configure Casbin model and policies programmatically without external files.
- **Advanced Decorators**: Use `@require` for complex authorization logic.
- **Resource Ownership**: Validate if users own the resources they are accessing.
- **Query Filtering**: Automatically filter SQLAlchemy queries based on user permissions.

## Installation

```bash
pip install fastapi-rbac
```

## Quick Start

```python
from fastapi_role import create_roles, CasbinConfig

# 1. Define roles
Role = create_roles(["ADMIN", "USER", "SUPERADMIN"])

# 2. Setup CasbinConfig
config = CasbinConfig()
config.add_policy(Role.ADMIN, "data", "read")

# 3. Initialize RBACService
# rbac_service = RBACService(db_session, config=config)
```

## License

MIT
