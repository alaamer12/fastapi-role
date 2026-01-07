# Getting Started with fastapi-role

Welcome to fastapi-role, the Pure General RBAC Engine! This guide will get you up and running in under 15 minutes.

## 🎯 What is Pure General RBAC?

fastapi-role is designed as a **pure general RBAC engine** with zero business assumptions:

- ✅ **No hardcoded business concepts** (customers, orders, etc.)
- ✅ **Framework agnostic** (FastAPI, Flask, Django, CLI)
- ✅ **Resource agnostic** (works with any resource type)
- ✅ **Configuration-driven** (behavior defined by data, not code)

## 🚀 Quick Installation

```bash
# Core RBAC engine (framework-agnostic)
pip install fastapi-role

# With FastAPI support
pip install fastapi-role[fastapi]

# With all framework support  
pip install fastapi-role[all]
```

## 📝 5-Minute Example

Let's create a simple document management system:

```python
from fastapi_role import RBACService, create_roles, require, Permission

# 1. Create roles for your domain (any domain!)
Role = create_roles(["admin", "editor", "viewer"], superadmin="admin")

# 2. Initialize RBAC service
rbac = RBACService()

# 3. Define your user model (implement UserProtocol)
from dataclasses import dataclass

@dataclass
class User:
    id: int
    email: str
    role: str
    # Add any fields you need - no restrictions!

# 4. Protect business functions (not just HTTP endpoints!)
@require(Role.EDITOR, Permission("document", "create"))
async def create_document(title: str, content: str, current_user: User, rbac: RBACService):
    """This function is protected regardless of how it's called"""
    return {
        "id": 123,
        "title": title,
        "content": content,
        "author": current_user.email
    }

@require(Role.VIEWER, Permission("document", "read"))
async def read_document(doc_id: int, current_user: User, rbac: RBACService):
    """Anyone with viewer role can read documents"""
    return {"id": doc_id, "title": "Sample Doc", "content": "..."}

# 5. Use with any framework - here's FastAPI
from fastapi import FastAPI, Depends

app = FastAPI()

def get_current_user() -> User:
    # Your authentication logic here
    return User(id=1, email="user@example.com", role="editor")

def get_rbac_service() -> RBACService:
    return rbac

@app.post("/documents")
async def create_document_endpoint(
    title: str,
    content: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    # Call the protected business function
    return await create_document(title, content, current_user, rbac_service)

@app.get("/documents/{doc_id}")
async def read_document_endpoint(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    return await read_document(doc_id, current_user, rbac_service)
```

That's it! You now have a working RBAC system. Let's run it:

```bash
# Save the code above as main.py
uvicorn main:app --reload

# Test the endpoints
curl -X POST "http://localhost:8000/documents" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Doc", "content": "Hello World"}'

curl "http://localhost:8000/documents/123"
```

## 🏗️ Core Concepts

### 1. Dynamic Roles

Create roles at runtime for any domain:

```python
# E-commerce domain
ecommerce_roles = create_roles(["admin", "seller", "buyer"], superadmin="admin")

# Content management domain
cms_roles = create_roles(["editor", "author", "reviewer"], superadmin="editor")

# SaaS application domain
saas_roles = create_roles(["owner", "admin", "member", "guest"], superadmin="owner")

# Gaming domain
game_roles = create_roles(["game_master", "player", "spectator"], superadmin="game_master")
```

### 2. Resource-Agnostic Access

The RBAC engine works with ANY resource type:

```python
# Traditional business resources
@require(Permission("order", "read"))
async def get_order(order_id: int, user: User, rbac: RBACService): pass

@require(Permission("customer", "update"))
async def update_customer(customer_id: int, user: User, rbac: RBACService): pass

# Creative domains
@require(Permission("spaceship", "launch"))
async def launch_spaceship(ship_id: int, user: User, rbac: RBACService): pass

@require(Permission("recipe", "cook"))
async def cook_recipe(recipe_id: int, user: User, rbac: RBACService): pass

@require(Permission("quantum_computer", "entangle"))
async def entangle_qubits(qc_id: int, user: User, rbac: RBACService): pass
```

### 3. Framework Independence

The same protected function works everywhere:

```python
@require(Role.ADMIN, Permission("system", "backup"))
async def backup_system(backup_type: str, user: User, rbac: RBACService):
    """This function works with FastAPI, Flask, Django, CLI, tests, etc."""
    return {"status": "backup_started", "type": backup_type}

# FastAPI usage
@app.post("/backup")
async def backup_endpoint(backup_type: str, user: User = Depends(get_user)):
    return await backup_system(backup_type, user, rbac)

# Flask usage
@app.route('/backup', methods=['POST'])
def backup_endpoint():
    user = get_current_user()
    backup_type = request.json['type']
    return jsonify(asyncio.run(backup_system(backup_type, user, rbac)))

# CLI usage
@click.command()
def backup_command():
    user = get_admin_user()
    result = asyncio.run(backup_system("full", user, rbac))
    print(result)

# Direct testing
async def test_backup():
    user = User(id=1, role="admin")
    result = await backup_system("incremental", user, rbac)
    assert result["status"] == "backup_started"
```

## 🔧 Configuration

### File-Based Configuration

Create `rbac_config.yaml`:

```yaml
roles:
  - admin
  - manager
  - user
superadmin: admin

policies:
  - subject: "role:admin"
    object: "*"
    action: "*"
  - subject: "role:manager"
    object: "project"
    action: "read,write"
  - subject: "role:user"
    object: "project"
    action: "read"

cache:
  enabled: true
  ttl_seconds: 300

behavior:
  default_deny: true
  log_denials: true
```

Load the configuration:

```python
from fastapi_role import CasbinConfig

config = CasbinConfig.from_file("rbac_config.yaml")
rbac = RBACService(config=config)
```

### Environment Configuration

```bash
export RBAC_ROLES="admin,manager,user"
export RBAC_SUPERADMIN_ROLE="admin"
export RBAC_CACHE_ENABLED="true"
export RBAC_CACHE_TTL="600"
export RBAC_DEFAULT_DENY="true"
```

```python
config = CasbinConfig.from_env(prefix="RBAC_")
rbac = RBACService(config=config)
```

### Programmatic Configuration

```python
config = CasbinConfig(
    roles=["owner", "admin", "member"],
    superadmin_role="owner",
    cache_enabled=True,
    cache_ttl_seconds=600,
    default_deny=True
)
rbac = RBACService(config=config)
```

## 🔌 Custom Providers

Customize behavior through providers:

### Custom Ownership Provider

```python
from fastapi_role.protocols import OwnershipProvider

class ProjectOwnershipProvider(OwnershipProvider):
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

# Register the provider
rbac.register_ownership_provider("project", ProjectOwnershipProvider(db_session))
```

### Custom Subject Provider

```python
from fastapi_role.protocols import SubjectProvider

class TenantSubjectProvider(SubjectProvider):
    def get_subject(self, user: UserProtocol) -> str:
        # Include tenant in subject for multi-tenant apps
        return f"user:{user.id}:tenant:{user.tenant_id}"

rbac = RBACService(subject_provider=TenantSubjectProvider())
```

## 🎨 Framework Examples

### FastAPI (Recommended)

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi_role import RBACService, create_roles, require, Permission

app = FastAPI()
Role = create_roles(["admin", "user"])
rbac = RBACService()

# Business functions (framework-agnostic)
@require(Role.ADMIN)
async def delete_user_business(user_id: int, current_user: User, rbac: RBACService):
    # Business logic here
    return {"deleted": user_id}

@require(Permission("user", "read"))
async def get_user_business(user_id: int, current_user: User, rbac: RBACService):
    # Business logic here
    return {"id": user_id, "name": "John Doe"}

# FastAPI endpoints (thin wrappers)
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(lambda: rbac)
):
    return await delete_user_business(user_id, current_user, rbac_service)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(lambda: rbac)
):
    return await get_user_business(user_id, current_user, rbac_service)
```

### Flask

```python
from flask import Flask, request, jsonify
import asyncio

app = Flask(__name__)
Role = create_roles(["admin", "user"])
rbac = RBACService()

# Same business functions work with Flask!
@require(Role.ADMIN)
async def delete_user_business(user_id: int, current_user: User, rbac: RBACService):
    return {"deleted": user_id}

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    current_user = get_current_user()  # Your auth logic
    result = asyncio.run(delete_user_business(user_id, current_user, rbac))
    return jsonify(result)
```

### Django

```python
from django.http import JsonResponse
from django.views import View
import asyncio

class DeleteUserView(View):
    async def delete(self, request, user_id):
        current_user = get_current_user(request)  # Your auth logic
        
        # Same business function works with Django!
        result = await delete_user_business(user_id, current_user, rbac)
        return JsonResponse(result)
```

### CLI Application

```python
import click
import asyncio

@click.group()
def cli():
    pass

@cli.command()
@click.argument('user_id', type=int)
def delete_user(user_id):
    """Delete a user (admin only)"""
    admin_user = get_admin_user()  # Your auth logic
    
    # Same business function works in CLI!
    result = asyncio.run(delete_user_business(user_id, admin_user, rbac))
    click.echo(f"Result: {result}")

if __name__ == '__main__':
    cli()
```

## 🔒 Advanced Authorization

### Multiple Requirements (AND Logic)

```python
# User must be BOTH manager AND have project permission
@require(Role.MANAGER, Permission("project", "delete"))
async def delete_project(project_id: int, user: User, rbac: RBACService):
    pass
```

### Multiple Decorators (OR Logic)

```python
# User must be EITHER admin OR (manager with project permission)
@require(Role.ADMIN)
@require(Role.MANAGER, Permission("project", "manage"))
async def manage_project(project_id: int, user: User, rbac: RBACService):
    pass
```

### Complex Privileges

```python
from fastapi_role import Privilege

# Define complex privilege
manager_privilege = Privilege(
    name="project_manager",
    roles=["manager", "lead"],
    permissions=[Permission("project", "write")],
    ownership_required=["project"],
    conditions={"department": "engineering"}
)

@require(manager_privilege)
async def update_project(project_id: int, user: User, rbac: RBACService):
    pass
```

### Resource Ownership

```python
from fastapi_role import ResourceRef

# Check ownership programmatically
async def get_project_details(project_id: int, user: User, rbac: RBACService):
    resource = ResourceRef("project", project_id)
    
    if await rbac.check_ownership(user, resource):
        # User owns the project
        return {"id": project_id, "details": "full details"}
    elif await rbac.can_access(user, resource, "read"):
        # User can read but doesn't own
        return {"id": project_id, "details": "limited details"}
    else:
        raise PermissionError("Access denied")
```

## 🧪 Testing

Testing RBAC-protected functions is straightforward:

```python
import pytest
from fastapi_role import RBACService, create_roles

@pytest.fixture
def rbac():
    return RBACService()

@pytest.fixture
def roles():
    return create_roles(["admin", "user"])

async def test_admin_function(rbac, roles):
    # Create test user
    admin_user = User(id=1, email="admin@test.com", role="admin")
    
    # Test the business function directly
    result = await delete_user_business(123, admin_user, rbac)
    assert result["deleted"] == 123

async def test_permission_denied(rbac, roles):
    # Create non-admin user
    regular_user = User(id=2, email="user@test.com", role="user")
    
    # Should raise permission error
    with pytest.raises(PermissionError):
        await delete_user_business(123, regular_user, rbac)
```

## 🚀 Next Steps

Now that you have the basics:

1. **Read the [API Reference](api-reference.md)** for complete documentation
2. **Check out [Examples](../examples/)** for real-world usage patterns
3. **Learn about [Provider Architecture](provider-architecture.md)** for customization
4. **See [Framework Integration](framework-integration.md)** for your specific framework

## 🤔 Common Questions

### Q: Can I use this with my existing user model?

**A:** Yes! Just make sure your user model has `id` and `role` properties. No other requirements.

```python
# Your existing model
class MyUser:
    def __init__(self, user_id, user_role, other_fields):
        self.id = user_id      # Required
        self.role = user_role  # Required
        self.other_fields = other_fields  # No restrictions
```

### Q: How do I handle multi-tenant applications?

**A:** Use a custom subject provider:

```python
class TenantSubjectProvider:
    def get_subject(self, user):
        return f"user:{user.id}:tenant:{user.tenant_id}"
```

### Q: Can I use this without a web framework?

**A:** Absolutely! It works with CLI apps, background jobs, scripts, etc.

### Q: How do I migrate from hardcoded roles?

**A:** Replace hardcoded enums with dynamic role creation:

```python
# Before
class Role(Enum):
    ADMIN = "admin"

# After  
Role = create_roles(["admin", "user"])
```

### Q: What if I need custom ownership logic?

**A:** Implement an ownership provider:

```python
class MyOwnershipProvider:
    async def check_ownership(self, user, resource_type, resource_id):
        # Your custom logic here
        return True
```

## 🎯 Key Takeaways

1. **Pure General RBAC**: Works with any domain, any resources
2. **Framework Agnostic**: Same code works everywhere
3. **Configuration-Driven**: Behavior defined by data, not code
4. **Provider-Based**: Customize everything through providers
5. **Business Function Protection**: Protect logic, not just endpoints

Ready to build secure applications with pure general RBAC? Let's go! 🚀