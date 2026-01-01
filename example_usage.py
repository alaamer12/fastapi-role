"""Example usage of the FastAPI RBAC library using the copied files."""

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

# Import from the copied RBAC files
from fastapi_rbac.rbac import (
    Permission,
    Privilege,
    ResourceOwnership,
    Role,
    require,
    rbac_service,
)

# Initialize FastAPI app
app = FastAPI(title="FastAPI RBAC Example")


# User model (must have id, email, role attributes)
class User(BaseModel):
    id: int
    email: str
    role: str
    username: str = ""
    full_name: str = ""


# Mock user database
users_db = {
    1: User(id=1, email="admin@example.com", role="superadmin", username="admin", full_name="Admin User"),
    2: User(id=2, email="manager@example.com", role="salesman", username="manager", full_name="Manager User"),
    3: User(id=3, email="user@example.com", role="customer", username="user", full_name="Regular User"),
}


# Mock authentication dependency
async def get_current_user() -> User:
    """Mock authentication - returns admin user for demo."""
    return users_db[1]  # Return admin user for demo


# Define custom privileges using the copied code
UserManagement = Privilege(
    roles=[Role.SUPERADMIN, Role.SALESMAN],
    permission=Permission("user", "update"),
    resource=ResourceOwnership("user")
)

ConfigurationAccess = Privilege(
    roles=Role.CUSTOMER | Role.SALESMAN,
    permission=Permission("configuration", "read")
)


# Example endpoints using the RBAC decorators

@app.get("/")
async def root():
    """Public endpoint - no authentication required."""
    return {"message": "FastAPI RBAC Example", "status": "running"}


@app.get("/admin-only")
@require(Role.SUPERADMIN)
async def admin_only(user: User = Depends(get_current_user)):
    """Superadmin-only endpoint."""
    return {"message": "Welcome, superadmin!", "user": user.username}


@app.get("/sales-access")
@require(Role.SALESMAN)
async def sales_access(user: User = Depends(get_current_user)):
    """Salesman-only endpoint."""
    return {"message": "Sales dashboard", "user": user.username}


@app.get("/users")
@require(Permission("user", "read"))
async def list_users(user: User = Depends(get_current_user)):
    """List users - requires user:read permission."""
    return {"users": list(users_db.values()), "requested_by": user.username}


@app.get("/users/{user_id}")
@require(ResourceOwnership("user"))
async def get_user(user_id: int, user: User = Depends(get_current_user)):
    """Get specific user - requires ownership of user resource."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": users_db[user_id], "requested_by": user.username}


@app.put("/users/{user_id}")
@require(UserManagement)
async def update_user(
    user_id: int, 
    user_data: dict, 
    user: User = Depends(get_current_user)
):
    """Update user - requires UserManagement privilege."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user (mock)
    updated_user = users_db[user_id].model_copy(update=user_data)
    users_db[user_id] = updated_user
    
    return {"message": "User updated", "user": updated_user, "updated_by": user.username}


@app.get("/configurations")
@require(ConfigurationAccess)
async def list_configurations(user: User = Depends(get_current_user)):
    """List configurations - requires ConfigurationAccess privilege."""
    configs = [
        {"id": 1, "name": "Window Config 1", "customer_id": 1},
        {"id": 2, "name": "Door Config 1", "customer_id": 2},
    ]
    return {"configurations": configs, "requested_by": user.username}


# Multiple decorators example (OR logic)
@app.get("/flexible-access")
@require(Role.SUPERADMIN)  # Superadmin can access
@require(Role.SALESMAN, Permission("configuration", "read"))  # OR Salesman with config:read
async def flexible_access(user: User = Depends(get_current_user)):
    """Flexible access - Superadmin OR (Salesman AND configuration:read)."""
    return {"message": "Access granted!", "user": user.username, "access_type": "flexible"}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "rbac": "enabled",
        "casbin_policies": len(rbac_service.enforcer.get_policy()),
        "cache_stats": rbac_service.get_cache_stats() if hasattr(rbac_service, 'get_cache_stats') else {}
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI RBAC Example...")
    print("Available endpoints:")
    print("  GET  /                    - Public endpoint")
    print("  GET  /admin-only          - Superadmin only")
    print("  GET  /sales-access        - Salesman only")
    print("  GET  /users               - Requires user:read permission")
    print("  GET  /users/{user_id}     - Requires user ownership")
    print("  PUT  /users/{user_id}     - Requires UserManagement privilege")
    print("  GET  /configurations      - Requires ConfigurationAccess privilege")
    print("  GET  /flexible-access     - Multiple authorization options")
    print("  GET  /health              - Health check")
    print("\nNote: All protected endpoints will use admin user for demo")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)