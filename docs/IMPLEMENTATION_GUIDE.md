# FastAPI RBAC - Complete Implementation Guide

This guide shows you how to integrate the FastAPI RBAC library into your FastAPI application.

## Table of Contents

1. [Installation](#installation)
2. [Basic Setup](#basic-setup)
3. [Configuration Files](#configuration-files)
4. [User Model Requirements](#user-model-requirements)
5. [Core Features](#core-features)
6. [Template Integration](#template-integration)
7. [Testing](#testing)
8. [Advanced Usage](#advanced-usage)
9. [Migration from Existing Code](#migration-from-existing-code)

## Installation

### From Source (Development)

```bash
# Clone or copy the fastapi-role directory to your project
cp -r fastapi-role /path/to/your/project/

# Install dependencies
cd fastapi-role
pip install -e .
```

### From PyPI (When Published)

```bash
pip install fastapi-role
```

## Basic Setup

### 1. Create Configuration Files

Create two files in your project root:

**rbac_model.conf**:
```ini
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act, eft

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow)) && !some(where (p.eft == deny))

[matchers]
m = g(r.sub, p.sub) && keyMatch2(r.obj, p.obj) && keyMatch2(r.act, p.act)
```

**rbac_policy.csv**:
```csv
p, superadmin, *, *, allow
p, admin, *, *, allow
p, manager, user, read, allow
p, manager, user, update, allow
p, manager, order, *, allow
p, user, user, read, allow
p, user, order, read, allow
p, user, order, create, allow
p, guest, *, read, allow
```

### 2. Initialize RBAC in Your FastAPI App

```python
from fastapi import FastAPI
from fastapi_rbac import RBACService

app = FastAPI()

# Initialize RBAC service
rbac_service = RBACService()
# Make it globally available
from fastapi_rbac.rbac import rbac_service as global_rbac
global_rbac.__dict__.update(rbac_service.__dict__)
```

## Configuration Files

### RBAC Model (rbac_model.conf)

The model defines how permissions are structured:

- **request_definition**: Defines request format (subject, object, action)
- **policy_definition**: Defines policy format with effect (allow/deny)
- **role_definition**: Defines role inheritance
- **policy_effect**: Defines how policies are combined
- **matchers**: Defines matching logic with wildcards

### RBAC Policy (rbac_policy.csv)

The policy file defines actual permissions:

```csv
# Format: p, subject, object, action, effect
p, admin, *, *, allow          # Admin can do anything
p, user, user, read, allow     # Users can read user data
p, user, order, create, allow  # Users can create orders
```

## User Model Requirements

Your User model must implement these attributes:

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    email: str  # Used as subject in Casbin
    role: str   # User's primary role
    
    # Optional additional fields
    username: str = ""
    full_name: str = ""
    is_active: bool = True
```

## Core Features

### 1. Role-Based Authorization

```python
from fastapi_rbac import Role, require

@app.get("/admin")
@require(Role.SUPERADMIN)
async def admin_only(user: User = Depends(get_current_user)):
    return {"message": "Admin access"}
```

### 2. Permission-Based Authorization

```python
from fastapi_rbac import Permission, require

@app.get("/users")
@require(Permission("user", "read"))
async def list_users(user: User = Depends(get_current_user)):
    return {"users": []}
```

### 3. Resource Ownership

```python
from fastapi_rbac import ResourceOwnership, require

@app.get("/users/{user_id}")
@require(ResourceOwnership("user"))
async def get_user(user_id: int, user: User = Depends(get_current_user)):
    # Automatically checks if user owns user_id resource
    return {"user": f"User {user_id}"}
```

### 4. Privilege Abstraction

```python
from fastapi_rbac import Privilege, Role, Permission, ResourceOwnership

# Define reusable privileges
UserManagement = Privilege(
    roles=[Role.ADMIN, Role.MANAGER],
    permission=Permission("user", "update"),
    resource=ResourceOwnership("user")
)

@app.put("/users/{user_id}")
@require(UserManagement)
async def update_user(user_id: int, user: User = Depends(get_current_user)):
    return {"message": f"User {user_id} updated"}
```

### 5. Role Composition

```python
from fastapi_rbac import Role

# Combine roles with bitwise OR
sales_roles = Role.SALESMAN | Role.PARTNER

@app.get("/sales-data")
@require(sales_roles)
async def sales_data(user: User = Depends(get_current_user)):
    return {"data": "sales info"}
```

### 6. Multiple Decorators (OR Logic)

```python
@app.get("/flexible")
@require(Role.ADMIN)                    # Admin can access
@require(Role.MANAGER, Permission("order", "read"))  # OR Manager with order:read
async def flexible_access(user: User = Depends(get_current_user)):
    return {"message": "Access granted"}
```

## Template Integration

### 1. Setup Template Integration

```python
from fastapi.templating import Jinja2Templates
from fastapi_rbac import RBACTemplateMiddleware

templates = Jinja2Templates(directory="templates")
rbac_templates = RBACTemplateMiddleware(templates)

@app.get("/dashboard")
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    return await rbac_templates.render_with_rbac(
        "dashboard.html",
        request,
        {"title": "Dashboard"}
    )
```

### 2. Use RBAC in Templates

```html
<!-- dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>Welcome, {{ current_user.username }}!</h1>
    
    <!-- Permission-based content -->
    {% if can('user:create') %}
        <button>Create User</button>
    {% endif %}
    
    <!-- Role-based content -->
    {% if has.role('ADMIN') %}
        <div class="admin-panel">
            <h2>Admin Tools</h2>
        </div>
    {% endif %}
    
    <!-- RBAC helper macros -->
    {% from "rbac_helpers.html" import rbac_button %}
    {{ rbac_button("Delete", "/delete", permission="user:delete", class="btn-danger") }}
</body>
</html>
```

### 3. RBAC Template Helpers

Copy the `rbac_helpers.html.jinja` file to your templates directory and use:

```html
<!-- Import helpers -->
{% from "rbac_helpers.html" import rbac_button, rbac_nav_item, protected_content %}

<!-- RBAC Button -->
{{ rbac_button("New User", "/users/new", permission="user:create", icon="➕") }}

<!-- RBAC Navigation -->
{{ rbac_nav_item("Users", "/users", permission="user:read", icon="👥") }}

<!-- Protected Content -->
{% call protected_content(permission="admin:access") %}
    <div>Admin-only content</div>
{% endcall %}
```

## Testing

### 1. Basic Test Setup

```python
import pytest
from fastapi_rbac.testing import MockUser, MockRBACService

@pytest.fixture
def mock_user():
    return MockUser(id=1, email="test@example.com", role="user")

@pytest.fixture
def mock_rbac():
    return MockRBACService()

def test_permission_check(mock_user, mock_rbac):
    # Grant permission
    mock_rbac.set_permission("test@example.com", "user", "read", True)
    
    # Test
    result = await mock_rbac.check_permission(mock_user, "user", "read")
    assert result is True
```

### 2. Test Decorators

```python
from fastapi_rbac import require, Role
from unittest.mock import patch

@pytest.mark.asyncio
async def test_require_decorator():
    @require(Role.ADMIN)
    async def protected_function(user):
        return "success"
    
    admin_user = MockUser(role="admin")
    
    with patch("fastapi_rbac.rbac._check_role_requirement", return_value=True):
        result = await protected_function(admin_user)
        assert result == "success"
```

### 3. Integration Tests

```python
from fastapi.testclient import TestClient

def test_protected_endpoint():
    client = TestClient(app)
    
    # Mock authentication
    with patch("app.get_current_user") as mock_auth:
        mock_auth.return_value = MockUser(role="admin")
        
        response = client.get("/admin")
        assert response.status_code == 200
```

## Advanced Usage

### 1. Custom Resource Ownership

```python
from fastapi_rbac import RBACService

class CustomRBACService(RBACService):
    async def check_resource_ownership(self, user, resource_type, resource_id):
        if resource_type == "project":
            # Custom logic for project ownership
            return await self.check_project_membership(user, resource_id)
        
        return await super().check_resource_ownership(user, resource_type, resource_id)
    
    async def check_project_membership(self, user, project_id):
        # Your custom logic here
        return True
```

### 2. Dynamic Policy Management

```python
# Add policies at runtime
rbac_service.add_policy("user@example.com", "document", "read", "allow")

# Remove policies
rbac_service.remove_policy("user@example.com", "document", "read", "allow")

# Assign roles
rbac_service.add_role_for_user("user@example.com", "manager")
```

### 3. Query Filtering

```python
from fastapi_rbac import RBACQueryFilter
from sqlalchemy import select

async def get_user_orders(user: User, db: Session):
    query = select(Order)
    
    # Automatically filter based on user access
    filtered_query = await RBACQueryFilter.filter_orders(query, user)
    
    result = await db.execute(filtered_query)
    return result.scalars().all()
```

## Migration from Existing Code

### 1. From Basic Role Checks

**Before:**
```python
@app.get("/admin")
async def admin_endpoint(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Access denied")
    return {"data": "admin data"}
```

**After:**
```python
@app.get("/admin")
@require(Role.ADMIN)
async def admin_endpoint(user: User = Depends(get_current_user)):
    return {"data": "admin data"}
```

### 2. From Manual Permission Checks

**Before:**
```python
@app.get("/users")
async def list_users(user: User = Depends(get_current_user)):
    if not has_permission(user, "user", "read"):
        raise HTTPException(403, "Access denied")
    return {"users": []}
```

**After:**
```python
@app.get("/users")
@require(Permission("user", "read"))
async def list_users(user: User = Depends(get_current_user)):
    return {"users": []}
```

### 3. From Template Permission Checks

**Before:**
```html
{% if user.role == 'admin' %}
    <button>Admin Action</button>
{% endif %}
```

**After:**
```html
{% if has.role('ADMIN') %}
    <button>Admin Action</button>
{% endif %}

<!-- Or even better -->
{{ rbac_button("Admin Action", "/admin", role="ADMIN") }}
```

## Best Practices

### 1. Policy Organization

- Keep policies in version control
- Use meaningful resource and action names
- Group related policies together
- Document policy changes

### 2. Role Design

- Use hierarchical roles (admin > manager > user)
- Keep role names consistent
- Avoid too many granular roles
- Consider role composition for flexibility

### 3. Performance

- Use caching for frequent permission checks
- Batch policy updates
- Monitor policy evaluation performance
- Clear caches when policies change

### 4. Security

- Always validate user input
- Log authorization failures
- Regularly audit policies
- Use principle of least privilege

## Troubleshooting

### Common Issues

1. **"RBAC service not available"**
   - Ensure RBACService is properly initialized
   - Check that configuration files exist and are valid

2. **"Permission denied" for valid users**
   - Verify policy file syntax
   - Check user email matches policy subject
   - Ensure role assignments are correct

3. **Template rendering errors**
   - Verify user is passed to template context
   - Check that RBAC helpers are properly imported
   - Ensure template files exist

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("fastapi_rbac").setLevel(logging.DEBUG)
```

This comprehensive guide should help you implement FastAPI RBAC in your application. The library provides a complete, production-ready RBAC solution with extensive testing and template integration.