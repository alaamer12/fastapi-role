"""
Configuration for the generic test application.
Uses dynamic roles and pure general RBAC - no business assumptions.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - completely generic"""
    
    # Application settings
    app_name: str = "Generic RBAC Test Application"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database settings
    database_url: str = "sqlite:///./test_app.db"
    
    # RBAC settings - dynamic and configurable
    rbac_roles: List[str] = ["admin", "manager", "user", "viewer"]
    rbac_superadmin_role: str = "admin"
    rbac_cache_enabled: bool = True
    rbac_cache_ttl: int = 300
    rbac_default_deny: bool = True
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        env_prefix = "APP_"


# Global settings instance
settings = Settings()


def get_rbac_model_text() -> str:
    """Get the RBAC model configuration text"""
    return """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act, eft

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow)) && !some(where (p.eft == deny))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""


def get_rbac_policies() -> List[List[str]]:
    """Get initial RBAC policies - generic resource-based policies"""
    return [
        # Admin can do everything
        ["admin", "document", "create"],
        ["admin", "document", "read"],
        ["admin", "document", "update"], 
        ["admin", "document", "delete"],
        ["admin", "project", "create"],
        ["admin", "project", "read"],
        ["admin", "project", "update"],
        ["admin", "project", "delete"],
        ["admin", "task", "create"],
        ["admin", "task", "read"],
        ["admin", "task", "update"],
        ["admin", "task", "delete"],
        ["admin", "user", "create"],
        ["admin", "user", "read"],
        ["admin", "user", "update"],
        ["admin", "user", "delete"],
        
        # Manager can manage projects and tasks, read users
        ["manager", "document", "create"],
        ["manager", "document", "read"],
        ["manager", "document", "update"],
        ["manager", "project", "create"],
        ["manager", "project", "read"],
        ["manager", "project", "update"],
        ["manager", "task", "create"],
        ["manager", "task", "read"],
        ["manager", "task", "update"],
        ["manager", "task", "delete"],
        ["manager", "user", "read"],
        
        # User can create and manage their own resources
        ["user", "document", "create"],
        ["user", "document", "read"],
        ["user", "project", "create"],
        ["user", "project", "read"],
        ["user", "task", "create"],
        ["user", "task", "read"],
        ["user", "task", "update"],
        ["user", "user", "read"],
        
        # Viewer can only read
        ["viewer", "document", "read"],
        ["viewer", "project", "read"],
        ["viewer", "task", "read"],
        ["viewer", "user", "read"],
    ]