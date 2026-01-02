"""Example usage of the FastAPI-Role library.

This example demonstrates the modern, dynamic way to use the library:
1. Dynamic Role creation.
2. Code-first Casbin configuration.
3. FastAPI integration with the @require decorator.
"""

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
from typing import Optional

# Import components from the generalized library
from fastapi_role import (
    create_roles,
    CasbinConfig,
    RBACService,
    require,
    Permission,
    Privilege,
    ResourceOwnership,
)

# --- 1. Define Your Roles ---
# Instead of a static Enum, we create them dynamically.
# This allows users of the library to define exactly what roles they need.
Role = create_roles(["SUPERADMIN", "SALESMAN", "PARTNER", "CUSTOMER"])

# --- 2. Configure Your Security Model ---
# No more .conf or .csv files! Everything is in code.
config = CasbinConfig()

# Add permission policies
config.add_policy(Role.CUSTOMER, "configuration", "read")
config.add_policy(Role.SALESMAN, "configuration", "write")
config.add_policy(Role.SALESMAN, "user", "read")

# Add role inheritance
# SALESMAN inherits everything CUSTOMER can do
config.add_role_inheritance(Role.SALESMAN, Role.CUSTOMER)
# SUPERADMIN inherits everything SALESMAN can do
config.add_role_inheritance(Role.SUPERADMIN, Role.SALESMAN)


# --- 3. Mock Setup ---
class User(BaseModel):
    id: int
    email: str
    role: str
    username: str = ""


# Mock database session for rbac_service
class MockSession:
    async def commit(self):
        pass

    async def rollback(self):
        pass


# Initialize the global rbac_service (usually done in app lifecycle)
db_session = MockSession()
rbac_service_instance = RBACService(db=db_session, config=config)

# --- 4. FastAPI App ---
app = FastAPI(title="FastAPI-Role Demo")


async def get_current_user() -> User:
    """Mock dependency to simulate a logged-in user."""
    # We'll return a SALESMAN for this demo
    return User(id=2, email="salesman@example.com", role=Role.SALESMAN.value, username="sales_pro")


# --- 5. Custom Privilege Definition ---
# Reusable bundle of role/permission/ownership logic
UserManagement = Privilege(
    roles=[Role.SUPERADMIN, Role.SALESMAN],
    permission=Permission("user", "update"),
    resource=ResourceOwnership("user"),
)

# --- 6. Protected Endpoints ---


@app.get("/")
async def public():
    return {"message": "Public access"}


@app.get("/config/read")
@require(Role.CUSTOMER)  # Salesman inherits this
async def read_config(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.username}, you can read configurations."}


@app.get("/config/write")
@require(Role.SALESMAN)
async def write_config(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.username}, you can write configurations."}


@app.get("/admin-only")
@require(Role.SUPERADMIN)
async def admin_only(user: User = Depends(get_current_user)):
    # This will fail for our mock salesman
    return {"message": "Admin only"}


@app.get("/user/{user_id}")
@require(UserManagement)
async def edit_user(user_id: int, user: User = Depends(get_current_user)):
    """Only Superadmin or the Salesman who owns the user record can access."""
    return {"message": f"Editing user {user_id}"}


if __name__ == "__main__":
    import uvicorn

    print("\n[FastAPI-Role] Demo started!")
    print(f"Active Roles: {list(Role.__members__.keys())}")
    print("Try accessing: http://localhost:8000/config/read")
    uvicorn.run(app, host="0.0.0.0", port=8000)
