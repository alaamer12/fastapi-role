# fastapi-role: Pure General RBAC Engine

**fastapi-role** is a framework-agnostic, business-agnostic Role-Based Access Control (RBAC) engine with zero assumptions about your application domain. Built on [Casbin](https://casbin.org/), it provides a pure, general-purpose RBAC system that works with any resource type, any framework, and any business domain.

## 🎯 Pure General RBAC Philosophy

Unlike traditional RBAC libraries that assume specific business models (users, customers, orders), fastapi-role is designed as a **pure general RBAC engine**:

- ✅ **Zero Business Assumptions**: No hardcoded roles, resources, or domain concepts
- ✅ **Framework Agnostic**: Works with FastAPI, Flask, Django, CLI apps, background jobs
- ✅ **Resource Agnostic**: Handles any resource type through `(type, id)` patterns
- ✅ **Provider-Based**: All business logic through pluggable providers
- ✅ **Configuration-Driven**: Behavior defined by data, not code
- ✅ **Dynamic Roles**: Create roles at runtime without code changes

## 🚀 Quick Start

### Installation

```bash
# Core RBAC engine (framework-agnostic)
pip install fastapi-role

# With FastAPI support
pip install fastapi-role[fastapi]

# With all framework support
pip install fastapi-role[all]
```

### Basic Usage

```python
from fastapi_role import RBACService, create_roles, Permission, require

# 1. Create dynamic roles for your domain
Role = create_roles(["admin", "manager", "user"], superadmin="admin")

# 2. Initialize RBAC service
rbac = RBACService()

# 3. Protect any function (not just HTTP endpoints)
@require(Role.MANAGER, Permission("documents", "read"))
async def get_document(doc_id: int, current_user: User, rbac_service: RBACService):
    """This function is protected regardless of how it's called"""
    # Your business logic here
    return {"id": doc_id, "content": "..."}

# 4. Use in FastAPI (or any framework)
from fastapi import FastAPI, Depends

app = FastAPI()

@app.get("/documents/{doc_id}")
async def get_document_endpoint(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    # Call the protected business function
    return await get_document(doc_id, current_user, rbac_service)
```

## 🏗️ Architecture: Pure General RBAC

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pure General RBAC Engine                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Core RBAC Engine                        │   │
│  │  • Dynamic role creation: create_roles(names)           │   │
│  │  • Resource-agnostic access: can_access(user,res,act)  │   │
│  │  • Generic privilege evaluation: evaluate(user,priv)   │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Provider Architecture                     │   │
│  │  • Subject Provider: extract_id(user)                  │   │
│  │  • Ownership Provider: check_owns(user,type,id)        │   │
│  │  • Policy Provider: load_policies(config)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Configuration System                        │   │
│  │  • No hardcoded roles or resources                     │   │
│  │  • Data-driven policy definitions                      │   │
│  │  • Runtime role and privilege definition               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Your Implementation
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Your Application Domain                      │
│  • Domain Models: User, Order, Project, Document, etc.         │
│  • Custom Ownership Rules: OrderOwner, ProjectManager, etc.    │
│  • Business Policies: roles.yaml, policies.csv, etc.          │
└─────────────────────────────────────────────────────────────────┘
```

## 🎨 Framework Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from fastapi_role import RBACService, create_roles, require, Permission

# Create roles for your application domain
Role = create_roles(["admin", "editor", "viewer"], superadmin="admin")

app = FastAPI()
rbac = RBACService()

# Protect business functions directly
@require(Role.EDITOR, Permission("articles", "create"))
async def create_article(title: str, content: str, current_user: User, rbac: RBACService):
    # Business logic - framework independent
    return {"title": title, "content": content, "author": current_user.id}

@app.post("/articles")
async def create_article_endpoint(
    article_data: ArticleCreate,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    return await create_article(
        article_data.title, 
        article_data.content, 
        current_user, 
        rbac_service
    )
```

### Flask Integration

```python
from flask import Flask, request, jsonify
from fastapi_role import RBACService, create_roles, require, Permission

app = Flask(__name__)
Role = create_roles(["admin", "user"])
rbac = RBACService()

# Same protected function works with Flask
@require(Role.ADMIN, Permission("users", "delete"))
async def delete_user(user_id: int, current_user: User, rbac: RBACService):
    # Business logic - same function as FastAPI example
    return {"deleted": user_id}

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user_endpoint(user_id):
    current_user = get_current_user()  # Your auth logic
    return jsonify(delete_user(user_id, current_user, rbac))
```

### CLI Application

```python
import asyncio
from fastapi_role import RBACService, create_roles, require, Permission

Role = create_roles(["admin", "operator"])
rbac = RBACService()

# Same protected function works in CLI
@require(Role.ADMIN, Permission("system", "backup"))
async def backup_database(current_user: User, rbac: RBACService):
    # Business logic - same function works everywhere
    print("Starting database backup...")
    return {"status": "backup_started"}

# CLI usage
async def main():
    admin_user = User(id=1, role="admin")
    result = await backup_database(admin_user, rbac)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔧 Resource-Agnostic Design

The core principle: **the RBAC engine never knows what your resources represent**.

```python
# ❌ Business-Coupled (Traditional)
rbac.get_accessible_customers(user)
rbac.get_accessible_orders(user)
rbac.check_customer_ownership(user, customer_id)

# ✅ Resource-Agnostic (fastapi-role)
rbac.can_access(user, ResourceRef("customer", customer_id), "read")
rbac.can_access(user, ResourceRef("order", order_id), "update")
rbac.evaluate(user, Permission("project", "delete"))
```

### Custom Resource Types

```python
# Works with ANY resource type
@require(Permission("spaceship", "launch"))
async def launch_spaceship(ship_id: int, user: User, rbac: RBACService):
    return {"ship_id": ship_id, "status": "launched"}

@require(Permission("recipe", "cook"))
async def cook_recipe(recipe_id: int, user: User, rbac: RBACService):
    return {"recipe_id": recipe_id, "status": "cooking"}

@require(Permission("quantum_computer", "entangle"))
async def entangle_qubits(qc_id: int, user: User, rbac: RBACService):
    return {"quantum_computer_id": qc_id, "entanglement": "active"}
```

## 🔌 Provider Architecture

Customize all business-specific behavior through providers:

### Custom Ownership Provider

```python
from fastapi_role.protocols import OwnershipProvider

class ProjectOwnershipProvider(OwnershipProvider):
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "project":
            # Your custom ownership logic
            project = await get_project(resource_id)
            return project.owner_id == user.id or user.id in project.collaborators
        return False

# Register the provider
rbac.register_ownership_provider("project", ProjectOwnershipProvider())
```

### Custom Subject Provider

```python
from fastapi_role.protocols import SubjectProvider

class CustomSubjectProvider(SubjectProvider):
    def get_subject(self, user: UserProtocol) -> str:
        # Use any field as the subject identifier
        return f"user:{user.id}:{user.tenant_id}"

rbac = RBACService(subject_provider=CustomSubjectProvider())
```

## 📊 Configuration-Driven Policies

Define all behavior through configuration, not code:

### YAML Configuration

```yaml
# roles.yaml
roles:
  - admin
  - manager  
  - user
superadmin: admin

# policies.yaml
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
```

### File-Based Configuration

```python
from fastapi_role import RBACService, CasbinConfig

config = CasbinConfig(
    model_path="model.conf",
    policy_path="policies.csv"
)

rbac = RBACService(config=config)
```

## 🎯 Dynamic Role System

Create roles at runtime without code changes:

```python
# Different applications, same RBAC engine
ecommerce_roles = create_roles(["admin", "seller", "buyer"], superadmin="admin")
cms_roles = create_roles(["editor", "author", "reviewer"], superadmin="editor")  
saas_roles = create_roles(["owner", "admin", "member", "guest"], superadmin="owner")

# Role composition
combined_role = Role.ADMIN | Role.MANAGER  # OR logic
```

## 🔒 Security Features

- **Privilege Escalation Prevention**: Strict role validation
- **Authorization Bypass Protection**: No hardcoded bypasses
- **Audit Trail**: Comprehensive logging of all access decisions
- **Thread Safety**: Safe for concurrent use
- **Performance Optimized**: Caching and efficient policy evaluation

## 🧪 Testing

The RBAC engine includes comprehensive property-based testing:

```python
# Property tests validate universal correctness
def test_role_creation_consistency():
    """For any valid role names, creating roles multiple times produces equivalent results"""
    
def test_resource_agnostic_access():
    """For any resource type and ID, access control works without knowing what it represents"""
    
def test_privilege_evaluation_determinism():
    """For any user and privilege, multiple evaluations return the same result"""
```

## 📚 Examples

### Minimal Example (5 minutes setup)

```python
from fastapi import FastAPI, Depends
from fastapi_role import RBACService, create_roles, require, Permission

# 1. Create roles
Role = create_roles(["admin", "user"])

# 2. Setup RBAC
rbac = RBACService()

# 3. Protect functions
@require(Role.ADMIN)
async def admin_only_function(current_user: User, rbac: RBACService):
    return {"message": "Admin access granted"}

# 4. Use with FastAPI
app = FastAPI()

@app.get("/admin")
async def admin_endpoint(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(lambda: rbac)
):
    return await admin_only_function(current_user, rbac_service)
```

### Multi-Tenant SaaS Example

```python
# Tenant-agnostic RBAC
Role = create_roles(["tenant_admin", "tenant_user", "global_admin"])

@require(Role.TENANT_ADMIN, Permission("tenant_data", "read"))
async def get_tenant_data(tenant_id: int, current_user: User, rbac: RBACService):
    # Business logic here
    pass

# Custom ownership for multi-tenancy
class TenantOwnershipProvider(OwnershipProvider):
    async def check_ownership(self, user: UserProtocol, resource_type: str, resource_id: Any) -> bool:
        if resource_type == "tenant_data":
            return user.tenant_id == resource_id
        return False
```

## 🔄 Migration from Business-Coupled Systems

Migrating from hardcoded business logic to pure general RBAC:

```python
# Before: Business-coupled
@require_customer_access
def get_customer_orders(customer_id: int):
    pass

# After: Resource-agnostic  
@require(Permission("order", "read"))
async def get_orders(resource_id: int, current_user: User, rbac: RBACService):
    pass
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- **Documentation**: [GitHub Repository](https://github.com/alaamer12/fastapi-role)
- **Issues**: [GitHub Issues](https://github.com/alaamer12/fastapi-role/issues)
- **PyPI**: [fastapi-role](https://pypi.org/project/fastapi-role/)
- **Casbin**: [Official Website](https://casbin.org/)

---

**fastapi-role**: Pure General RBAC Engine - Because authorization shouldn't assume your business domain.
