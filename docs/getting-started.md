# Getting Started with fastapi-role

`fastapi-role` is a flexible, pluggable Role-Based Access Control (RBAC) library for FastAPI applications, powered by [Casbin](https://casbin.org/).

## Installation

Install using pip:

```bash
pip install fastapi-role
```

Or using poetry:

```bash
poetry add fastapi-role
```

Or using uv:

```bash
uv add fastapi-role
```

## Quick Start

Here's a minimal example to secure a FastAPI application.

### 1. Create a minimal application

Create a file named `main.py`:

```python
from fastapi import FastAPI, Depends
from fastapi_role import RBACService, Role, UserProtocol, require
from fastapi_role.core.config import CasbinConfig
from typing import Annotated

# 1. Define your User model (implementing UserProtocol)
class User:
    def __init__(self, id: int, email: str, role: str):
        self.id = id
        self.email = email
        self.role = role

# 2. Configure RBAC
# By default, this creates a 'roles' directory in your user data folder
config = CasbinConfig(app_name="my_fastapi_app")

# 3. Initialize Service (in a real app, use dependency injection)
# We use a mock DB session here since we aren't using DB features yet
rbac_service = RBACService(db=None, config=config)

app = FastAPI()

# 4. Create a dependency to get the current user
def get_current_user():
    # In a real app, this would validate a token
    return User(id=1, email="alice@example.com", role="admin")

CurrentUser = Annotated[User, Depends(get_current_user)]

# 5. Protect Endpoints
@app.get("/admin-only")
@require(roles=["admin"])  # Only users with 'admin' role can access
async def admin_dashboard(user: CurrentUser):
    return {"message": f"Welcome admin {user.email}!"}

@app.get("/public")
async def public_endpoint():
    return {"message": "Hello world!"}
```

### 2. Run the application

```bash
uvicorn main:app --reload
```

### 3. Test the endpoints

- **GET /public**: Should return `200 OK`.
- **GET /admin-only**: Should return `200 OK` (since our mock user is an admin).

Try changing the user's role to "guest" in `get_current_user` and accessing `/admin-only` again. You should get a `403 Forbidden` error.

## Core Concepts

### User Protocol

Your user objects don't need to inherit from any specific class. They just need to match the `UserProtocol`:

```python
class UserProtocol(Protocol):
    id: Union[int, str]
    email: str
    role: str
```

### Roles

You can use simple strings for roles, or typically you'll define them in your configuration. The library comes with a flexible role system.

### Permissions

Permissions are defined in a Casbin policy file (`rbac_policy.csv`). By default, `fastapi-role` helps you generate one.

A standard policy rule looks like:
```csv
p, role_name, resource, action
```

Example:
```csv
p, admin, users, read
p, admin, users, write
p, guest, posts, read
```

### Checking Permissions

You can check permissions explicitly in your code:

```python
if await rbac_service.check_permission(user, "users", "write"):
    # Do something sensitive
    pass
```

## Next Steps

- Learn how to [Configure](configuration.md) policies and roles.
- Understand the [Architecture](architecture.md).
- Integrate with [SQLAlchemy](examples/database/).
