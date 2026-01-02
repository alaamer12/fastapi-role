"""Comprehensive example demonstrating the full usage of fastapi-role.

This example covers:
1. Dynamic role creation.
2. Bitwise role composition.
3. Code-first Casbin configuration.
4. RBACService initialization.
5. FastAPI route protection using the @require decorator.
6. Mocking user models and database sessions for a standalone demonstration.
"""

import sys
from typing import Optional
from fastapi import FastAPI, Depends, Request
from pydantic import BaseModel

# In a real project, you'd install the package and import from it:
# from fastapi_role import create_roles, CasbinConfig, RBACService, require, Permission

# For this demo, we assume the library is in the python path
try:
    from fastapi_role import (
        create_roles,
        CasbinConfig,
        RBACService,
        require,
        Permission,
        RoleComposition
    )
except ImportError:
    print("Error: fastapi-role library not found in path.")
    sys.exit(1)

# --- 1. Define Dynamic Roles ---
# We create our roles once at startup.
Role = create_roles(["SUPERADMIN", "ADMIN", "EDITOR", "VIEWER", "USER"])

# --- 2. Code-First Casbin Configuration ---
# Define your security model and policies purely in Python.
config = CasbinConfig()

# Basic permission policies (p)
# Format: add_policy(subject, resource, action)
config.add_policy(Role.VIEWER, "article", "read")
config.add_policy(Role.EDITOR, "article", "edit")
config.add_policy(Role.ADMIN, "user_management", "write")

# Role Inheritance (g)
# Format: add_role_inheritance(child_role, parent_role)
# EDITOR inherits everything VIEWER can do
config.add_role_inheritance(Role.EDITOR, Role.VIEWER)
# ADMIN inherits everything EDITOR can do
config.add_role_inheritance(Role.ADMIN, Role.EDITOR)
# SUPERADMIN is a special case often handled in logic, but can be added here too
config.add_role_inheritance(Role.SUPERADMIN, Role.ADMIN)

# --- 3. Mock Models for Demonstration ---
class User(BaseModel):
    """Simple User model matching the protocol required by RBACService."""
    id: int
    email: str
    role: str

# Mock Database session required by RBACService (which inherits from BaseService)
# In reality, this would be an AsyncSession from SQLAlchemy.
class MockDB:
    async def commit(self): pass
    async def rollback(self): pass

# --- 4. Initialize RBAC Service ---
# Usually done in a dependency or global context
mock_db = MockDB()
rbac_service = RBACService(db=mock_db, config=config)

# --- 5. FastAPI Application Setup ---
app = FastAPI(title="FastAPI-Role Comprehensive Example")

async def get_current_user(request: Request) -> User:
    """Dependency to simulate a logged-in user.
    
    Usually, you would extract this from a JWT token.
    """
    # Simulate an EDITOR user for this demo
    return User(id=1, email="editor@example.com", role=Role.EDITOR.value)

# --- 6. Protected Routes ---

@app.get("/public")
async def public_zone():
    """Zone accessible to everyone."""
    return {"message": "Hello World"}

@app.get("/articles/read")
@require(Role.VIEWER)  # Requires VIEWER role (EDITOR inherits this)
async def read_articles(user: User = Depends(get_current_user)):
    """Protected by base role."""
    return {"message": f"Welcome {user.email}, you can read articles."}

@app.get("/articles/edit")
@require(Role.EDITOR)  # Requires EDITOR role
async def edit_articles(user: User = Depends(get_current_user)):
    """Protected by specific role."""
    return {"message": f"Hello {user.email}, you have permission to edit."}

@app.get("/management")
@require(Role.ADMIN | Role.SUPERADMIN)  # Chained roles using bitwise OR
async def admin_portal(user: User = Depends(get_current_user)):
    """Protected by a composition of roles."""
    return {"message": "Admin portal accessed."}

@app.get("/custom-permission")
@require(Permission("article", "publish")) # Permission-based check
async def publish_article(user: User = Depends(get_current_user)):
    """Protected by specific action permission."""
    # Note: For this to pass for our EDITOR, we'd need to add the policy
    # config.add_policy(Role.EDITOR, "article", "publish")
    return {"message": "Article published!"}

# --- 7. Usage Implementation ---
if __name__ == "__main__":
    import uvicorn
    print("\n--- FastAPI-Role Example ---")
    print(f"Roles created: {Role.__members__.keys()}")
    print("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
