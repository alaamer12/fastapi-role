# Minimal Pure RBAC Example

This example demonstrates the pure general RBAC system in a single FastAPI file with no business assumptions.

## Features

- **Pure General RBAC**: No hardcoded business concepts or assumptions
- **Dynamic Roles**: Roles created at runtime from configuration
- **Generic Resources**: Works with any resource type (document, project, task, etc.)
- **In-Memory Configuration**: No external files required
- **Framework-Agnostic Decorators**: RBAC decorators work with any function

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install fastapi uvicorn python-jose[cryptography] python-multipart
   ```

2. **Run the Application**:
   ```bash
   python examples/minimal_rbac_example.py
   ```

3. **Access the API**:
   - Application: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Interactive API: http://localhost:8000/redoc

## Test Users

The example includes three test users with different roles:

| Email | Role | Password | Capabilities |
|-------|------|----------|-------------|
| admin@example.com | admin | password | Full access to everything |
| manager@example.com | manager | password | Read all, create documents/projects/tasks |
| user@example.com | user | password | Read public resources, create tasks |

## API Endpoints

### Authentication
- `POST /login` - Login with email/password
- `GET /me` - Get current user info

### Resources (Generic)
- `GET /resources` - List accessible resources
- `GET /resources/{type}` - Filter by resource type
- `GET /resources/{type}/{id}` - Get specific resource
- `POST /resources/{type}` - Create new resource
- `PUT /resources/{type}/{id}` - Update resource
- `DELETE /resources/{type}/{id}` - Delete resource

### Admin (Role-Based)
- `GET /admin/users` - List all users (admin only)
- `GET /admin/stats` - System statistics (admin only)

## Testing the RBAC System

1. **Login as different users**:
   ```bash
   curl -X POST "http://localhost:8000/login" \
        -H "Content-Type: application/json" \
        -d '{"email": "admin@example.com", "password": "password"}'
   ```

2. **Use the token in subsequent requests**:
   ```bash
   curl -X GET "http://localhost:8000/resources" \
        -H "Authorization: Bearer YOUR_TOKEN_HERE"
   ```

3. **Test access control**:
   - Admin can access everything
   - Manager can read all, create resources
   - User can only read public resources and create tasks

## Key RBAC Concepts Demonstrated

### 1. Dynamic Role Creation
```python
# Roles created at runtime from configuration
ROLE_NAMES = ["admin", "manager", "user"]
Role = create_roles(ROLE_NAMES)
```

### 2. Generic Resource Types
```python
# No hardcoded business concepts
RESOURCE_TYPES = ["document", "project", "task"]
```

### 3. Resource-Agnostic Access Control
```python
@require(CorePermission("*", "read"))
async def list_resources(current_user, rbac):
    # Works with any resource type
    can_access = await rbac.can_access(user, resource.to_resource_ref(), "read")
```

### 4. Framework-Agnostic Decorators
```python
# Decorators protect business functions, not just HTTP endpoints
@require(CorePermission("*", "delete"))
async def delete_resource(resource_type, resource_id, current_user, rbac):
    # Function can be called from HTTP, CLI, background job, etc.
```

### 5. Provider-Based Architecture
```python
# Custom ownership logic through providers
class MinimalOwnershipProvider:
    async def check_ownership(self, user, resource_type, resource_id):
        # Custom business logic here
        return user.id == resource.owner_id or resource.is_public
```

## Configuration

The example uses in-memory configuration with no external files:

```python
def create_rbac_config():
    config = CasbinConfig(
        app_name="minimal-rbac-example",
        superadmin_role="admin"
    )
    
    # Add policies programmatically
    config.add_policy("admin", "*", "*")
    config.add_policy("manager", "*", "read")
    config.add_policy("user", "*", "read")
    
    return config
```

## Extending the Example

This minimal example can be extended by:

1. **Adding new resource types**: Just add to `RESOURCE_TYPES`
2. **Adding new roles**: Add to `ROLE_NAMES` and update policies
3. **Custom ownership logic**: Implement custom ownership providers
4. **Database integration**: Replace in-memory storage with database
5. **Complex policies**: Add attribute-based or context-aware policies

## No Business Assumptions

This example demonstrates that the RBAC system makes no assumptions about:
- What resources represent (could be orders, customers, files, etc.)
- What roles mean (could be salesman, doctor, teacher, etc.)  
- What actions are available (could be approve, diagnose, grade, etc.)
- How ownership works (completely customizable through providers)

The system is truly domain-agnostic and works with any application.