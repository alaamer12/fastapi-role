"""Integration tests for test application - Task 10.3.

This module provides comprehensive integration testing for the test FastAPI application
to validate that the pure general RBAC system works correctly across all endpoints.

Test Classes:
    TestAuthenticationIntegration: Tests authentication flows and JWT handling
    TestUserManagementIntegration: Tests user CRUD operations with various roles
    TestDocumentManagementIntegration: Tests document operations with ownership validation
    TestProjectManagementIntegration: Tests project operations with complex authorization
    TestTaskManagementIntegration: Tests task operations with nested resource validation
    TestOwnershipValidationIntegration: Tests ownership validation across all resource types
    TestErrorHandlingIntegration: Tests error handling and response formatting
    TestCrossResourceIntegration: Tests interactions between different resource types
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from test_fastapi.main import app
from test_fastapi.database import get_db, Base
from test_fastapi.models import User, Document, Project, Task
from test_fastapi.auth import create_access_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Override RBAC service for testing
def override_get_rbac_service():
    """Override RBAC service dependency for testing"""
    from test_fastapi.rbac_setup import create_rbac_service
    return create_rbac_service()

from test_fastapi.rbac_setup import get_rbac_service
app.dependency_overrides[get_rbac_service] = override_get_rbac_service


@pytest.fixture(scope="function")
def test_db():
    """Create test database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_users(test_db):
    """Create test users with different roles"""
    db = TestingSessionLocal()
    
    users = [
        User(id=1, email="admin@test.com", name="Admin User", role="admin", is_active=True),
        User(id=2, email="manager@test.com", name="Manager User", role="manager", is_active=True),
        User(id=3, email="user@test.com", name="Regular User", role="user", is_active=True),
        User(id=4, email="viewer@test.com", name="Viewer User", role="viewer", is_active=True),
        User(id=5, email="inactive@test.com", name="Inactive User", role="user", is_active=False),
    ]
    
    for user in users:
        db.add(user)
    
    db.commit()
    
    # Create access tokens for each user
    tokens = {}
    for user in users:
        if user.is_active:
            tokens[user.role] = create_access_token(data={"sub": user.email})
    
    # Reset the global RBAC service to ensure it uses the test database
    from test_fastapi.rbac_setup import _rbac_service
    import test_fastapi.rbac_setup as rbac_setup_module
    rbac_setup_module._rbac_service = None
    
    db.close()
    return {"users": users, "tokens": tokens}


@pytest.fixture(scope="function")
def test_resources(test_db, test_users):
    """Create test resources (documents, projects, tasks)"""
    db = TestingSessionLocal()
    
    # Create documents
    documents = [
        Document(id=1, title="Public Doc", content="Public content", owner_id=3, is_public=True),
        Document(id=2, title="Private Doc", content="Private content", owner_id=3, is_public=False),
        Document(id=3, title="Manager Doc", content="Manager content", owner_id=2, is_public=False),
    ]
    
    # Create projects
    projects = [
        Project(id=1, name="Public Project", description="Public project", owner_id=3, is_public=True),
        Project(id=2, name="Private Project", description="Private project", owner_id=3, is_public=False),
        Project(id=3, name="Manager Project", description="Manager project", owner_id=2, is_public=False),
    ]
    
    # Create tasks
    tasks = [
        Task(id=1, title="User Task", description="User's task", assignee_id=3, project_id=1),
        Task(id=2, title="Manager Task", description="Manager's task", assignee_id=2, project_id=2),
        Task(id=3, title="Standalone Task", description="No project task", assignee_id=3, project_id=None),
    ]
    
    for resource_list in [documents, projects, tasks]:
        for resource in resource_list:
            db.add(resource)
    
    db.commit()
    db.close()
    
    return {
        "documents": documents,
        "projects": projects,
        "tasks": tasks
    }


def get_auth_headers(token: str) -> Dict[str, str]:
    """Get authorization headers for requests"""
    return {"Authorization": f"Bearer {token}"}


class TestAuthenticationIntegration:
    """Tests authentication flows and JWT handling.
    
    Validates: Authentication, JWT token handling, user session management
    """
    
    def test_login_success(self, client, test_users):
        """Test successful login with valid user"""
        response = client.post("/auth/login", json={"email": "admin@test.com"})
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_email"] == "admin@test.com"
        assert data["user_role"] == "admin"
    
    def test_login_invalid_user(self, client, test_users):
        """Test login with non-existent user"""
        response = client.post("/auth/login", json={"email": "nonexistent@test.com"})
        
        assert response.status_code == 401
        assert "Invalid email or user not found" in response.json()["detail"]
    
    def test_login_inactive_user(self, client, test_users):
        """Test login with inactive user"""
        response = client.post("/auth/login", json={"email": "inactive@test.com"})
        
        assert response.status_code == 401
        assert "Invalid email or user not found" in response.json()["detail"]
    
    def test_protected_endpoint_without_token(self, client, test_users):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/users/")
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_invalid_token(self, client, test_users):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/users/", headers=headers)
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_valid_token(self, client, test_users):
        """Test accessing protected endpoint with valid token"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/users/", headers=headers)
        
        assert response.status_code == 200
    
    def test_get_current_user_info(self, client, test_users):
        """Test getting current user information"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@test.com"
        assert data["role"] == "user"
    
    def test_logout(self, client, test_users):
        """Test logout endpoint"""
        response = client.post("/auth/logout")
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
    
    def test_get_test_users(self, client, test_users):
        """Test getting list of test users for development"""
        response = client.get("/auth/test-users")
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) == 5  # All users including inactive


class TestUserManagementIntegration:
    """Tests user CRUD operations with various roles.
    
    Validates: User management permissions, role-based access control, data validation
    """
    
    def test_list_users_admin(self, client, test_users):
        """Test admin can list all users"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/users/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert data["total"] == 5  # All users including inactive
    
    def test_list_users_manager(self, client, test_users):
        """Test manager can list users (has read permission)"""
        headers = get_auth_headers(test_users["tokens"]["manager"])
        response = client.get("/users/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
    
    def test_list_users_viewer_allowed(self, client, test_users):
        """Test viewer can list users (has read permission in config)"""
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.get("/users/", headers=headers)
        
        # Viewer has user:read permission according to config, so this should work
        assert response.status_code == 200
    
    def test_get_user_by_id(self, client, test_users):
        """Test getting specific user by ID"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/users/1", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["email"] == "admin@test.com"
    
    def test_get_nonexistent_user(self, client, test_users):
        """Test getting non-existent user returns 404"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/users/999", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_create_user_admin(self, client, test_users):
        """Test admin can create new user"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        user_data = {
            "email": "newuser@test.com",
            "name": "New User",
            "role": "user",
            "is_active": True
        }
        
        response = client.post("/users/", json=user_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "user"
    
    def test_create_user_invalid_role(self, client, test_users):
        """Test creating user with invalid role fails"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        user_data = {
            "email": "newuser@test.com",
            "name": "New User",
            "role": "invalid_role",
            "is_active": True
        }
        
        response = client.post("/users/", json=user_data, headers=headers)
        
        assert response.status_code == 400
        assert "Invalid role" in response.json()["detail"]
    
    def test_create_user_duplicate_email(self, client, test_users):
        """Test creating user with duplicate email fails"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        user_data = {
            "email": "admin@test.com",  # Already exists
            "name": "Duplicate User",
            "role": "user",
            "is_active": True
        }
        
        response = client.post("/users/", json=user_data, headers=headers)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_user_insufficient_permission(self, client, test_users):
        """Test user without create permission cannot create users"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        user_data = {
            "email": "newuser@test.com",
            "name": "New User",
            "role": "user",
            "is_active": True
        }
        
        response = client.post("/users/", json=user_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_update_user_admin(self, client, test_users):
        """Test admin can update user"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        update_data = {
            "name": "Updated Name",
            "role": "manager"
        }
        
        response = client.put("/users/3", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["role"] == "manager"
    
    def test_update_user_insufficient_permission(self, client, test_users):
        """Test user without update permission cannot update users"""
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        update_data = {"name": "Updated Name"}
        
        response = client.put("/users/3", json=update_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_delete_user_admin(self, client, test_users):
        """Test admin can delete user"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        response = client.delete("/users/5", headers=headers)  # Delete inactive user
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_delete_self_forbidden(self, client, test_users):
        """Test user cannot delete their own account"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        response = client.delete("/users/1", headers=headers)  # Admin trying to delete self
        
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]
    
    def test_get_my_profile(self, client, test_users):
        """Test user can get their own profile"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.get("/users/me/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@test.com"
    
    def test_update_my_profile(self, client, test_users):
        """Test user can update their own profile"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        update_data = {"name": "Updated User Name"}
        
        response = client.put("/users/me/profile", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated User Name"

class TestDocumentManagementIntegration:
    """Tests document operations with ownership validation.
    
    Validates: Document CRUD, ownership-based access, visibility controls
    """
    
    def test_list_documents_admin(self, client, test_users, test_resources):
        """Test admin can see all documents"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/documents/?include_private=true", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # All documents
    
    def test_list_documents_user_visibility(self, client, test_users, test_resources):
        """Test user sees only public documents and their own"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/documents/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # Should see: Public Doc (public) + Private Doc (owns) = 2 documents
        assert data["total"] == 2
    
    def test_get_document_owner_access(self, client, test_users, test_resources):
        """Test document owner can access their private document"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/documents/2", headers=headers)  # Private Doc owned by user
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["title"] == "Private Doc"
    
    def test_get_document_access_denied(self, client, test_users, test_resources):
        """Test user cannot access other's private document"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/documents/3", headers=headers)  # Manager's private doc
        
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
    
    def test_get_public_document_access(self, client, test_users, test_resources):
        """Test any user can access public documents"""
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.get("/documents/1", headers=headers)  # Public Doc
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] == True
    
    def test_create_document(self, client, test_users):
        """Test user can create document"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        doc_data = {
            "title": "New Document",
            "content": "New content",
            "is_public": False
        }
        
        response = client.post("/documents/", json=doc_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Document"
        assert data["owner_id"] == 3  # User's ID
    
    def test_update_document_owner(self, client, test_users, test_resources):
        """Test document owner can update their document"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        update_data = {
            "title": "Updated Document Title",
            "content": "Updated content"
        }
        
        response = client.put("/documents/2", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Document Title"
    
    def test_update_document_admin_permission(self, client, test_users, test_resources):
        """Test admin can update any document"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        update_data = {"title": "Admin Updated Title"}
        
        response = client.put("/documents/3", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Admin Updated Title"
    
    def test_update_document_access_denied(self, client, test_users, test_resources):
        """Test user cannot update others' documents without permission"""
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        update_data = {"title": "Unauthorized Update"}
        
        response = client.put("/documents/2", json=update_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_delete_document_owner(self, client, test_users, test_resources):
        """Test document owner can delete their document"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.delete("/documents/2", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_get_my_documents(self, client, test_users, test_resources):
        """Test user can get their own documents"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.get("/documents/my/documents", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # User owns documents 1 and 2
        assert data["total"] == 2
    
    def test_make_document_public(self, client, test_users, test_resources):
        """Test owner can make document public"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.post("/documents/2/make-public", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] == True
    
    def test_make_document_private(self, client, test_users, test_resources):
        """Test owner can make document private"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.post("/documents/1/make-private", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] == False
class TestProjectManagementIntegration:
    """Tests project operations with complex authorization.
    
    Validates: Project CRUD, hierarchical permissions, status management
    """
    
    def test_list_projects_with_filters(self, client, test_users, test_resources):
        """Test listing projects with status and visibility filters"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/projects/?status_filter=active&include_private=true", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
    
    def test_get_project_hierarchical_access(self, client, test_users, test_resources):
        """Test project access with hierarchical permissions"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/projects/1", headers=headers)  # Public project
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] == True
    
    def test_create_project(self, client, test_users):
        """Test creating new project"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        project_data = {
            "name": "New Project",
            "description": "New project description",
            "status": "active",
            "is_public": False
        }
        
        response = client.post("/projects/", json=project_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["owner_id"] == 3  # User's ID
    
    def test_update_project_owner(self, client, test_users, test_resources):
        """Test project owner can update project"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description"
        }
        
        response = client.put("/projects/1", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
    
    def test_delete_project_with_tasks_forbidden(self, client, test_users, test_resources):
        """Test cannot delete project that has tasks"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.delete("/projects/1", headers=headers)  # Has tasks
        
        assert response.status_code == 400
        assert "Cannot delete project with" in response.json()["detail"]
    
    def test_get_project_tasks(self, client, test_users, test_resources):
        """Test getting tasks for a project"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.get("/projects/1/tasks", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_my_projects(self, client, test_users, test_resources):
        """Test getting user's own projects"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.get("/projects/my/projects", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # User owns projects 1 and 2
        assert data["total"] == 2
    
    def test_archive_project(self, client, test_users, test_resources):
        """Test archiving project"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.post("/projects/1/archive", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"
    
    def test_activate_project(self, client, test_users, test_resources):
        """Test activating project"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        # First archive it
        client.post("/projects/1/archive", headers=headers)
        
        # Then activate it
        response = client.post("/projects/1/activate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"


class TestTaskManagementIntegration:
    """Tests task operations with nested resource validation.
    
    Validates: Task CRUD, nested authorization, assignee management
    """
    
    def test_list_tasks_with_filters(self, client, test_users, test_resources):
        """Test listing tasks with multiple filters"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get("/tasks/?status_filter=todo&priority_filter=medium&project_id=1", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
    
    def test_get_task_assignee_access(self, client, test_users, test_resources):
        """Test task assignee can access their task"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/tasks/1", headers=headers)  # User's task
        
        assert response.status_code == 200
        data = response.json()
        assert data["assignee_id"] == 3  # User's ID
    
    def test_get_task_project_access(self, client, test_users, test_resources):
        """Test access to task through project ownership"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.get("/tasks/1", headers=headers)  # Task in user's project
        
        assert response.status_code == 200
    
    def test_create_task_in_project(self, client, test_users, test_resources):
        """Test creating task in project with validation"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        task_data = {
            "title": "New Task",
            "description": "New task description",
            "project_id": 1,  # User's project
            "status": "todo",
            "priority": "high"
        }
        
        response = client.post("/tasks/", json=task_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["project_id"] == 1
    
    def test_create_task_invalid_project(self, client, test_users, test_resources):
        """Test creating task in non-existent project fails"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        task_data = {
            "title": "New Task",
            "project_id": 999,  # Non-existent project
        }
        
        response = client.post("/tasks/", json=task_data, headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_create_task_unauthorized_project(self, client, test_users, test_resources):
        """Test creating task in unauthorized project fails"""
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        task_data = {
            "title": "New Task",
            "project_id": 2,  # User's private project, viewer can't access
        }
        
        response = client.post("/tasks/", json=task_data, headers=headers)
        
        assert response.status_code == 403
        assert "cannot create tasks in this project" in response.json()["detail"]
    
    def test_update_task_assignee(self, client, test_users, test_resources):
        """Test task assignee can update their task"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        update_data = {
            "title": "Updated Task Title",
            "status": "in_progress"
        }
        
        response = client.put("/tasks/1", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Task Title"
        assert data["status"] == "in_progress"
    
    def test_update_task_move_project(self, client, test_users, test_resources):
        """Test moving task to different project"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        update_data = {"project_id": 2}  # Move to user's other project
        
        response = client.put("/tasks/1", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == 2
    
    def test_delete_task_assignee(self, client, test_users, test_resources):
        """Test task assignee can delete their task"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.delete("/tasks/3", headers=headers)  # Standalone task
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_get_my_tasks(self, client, test_users, test_resources):
        """Test getting user's assigned tasks"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.get("/tasks/my/tasks", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # User is assigned to tasks 1 and 3
        assert data["total"] == 2
    
    def test_complete_task(self, client, test_users, test_resources):
        """Test marking task as complete"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.post("/tasks/1/complete", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
    
    def test_start_task(self, client, test_users, test_resources):
        """Test starting task"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        response = client.post("/tasks/1/start", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
class TestOwnershipValidationIntegration:
    """Tests ownership validation across all resource types.
    
    Validates: Ownership providers work correctly, ownership checks are enforced
    """
    
    def test_document_ownership_validation(self, client, test_users, test_resources):
        """Test document ownership is properly validated"""
        # Owner can update
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.put("/documents/2", json={"title": "Owner Update"}, headers=headers)
        assert response.status_code == 200
        
        # Non-owner cannot update (without admin permission)
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.put("/documents/2", json={"title": "Non-owner Update"}, headers=headers)
        assert response.status_code == 403
    
    def test_project_ownership_validation(self, client, test_users, test_resources):
        """Test project ownership is properly validated"""
        # Owner can update
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.put("/projects/1", json={"name": "Owner Update"}, headers=headers)
        assert response.status_code == 200
        
        # Non-owner cannot update (without admin permission)
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.put("/projects/1", json={"name": "Non-owner Update"}, headers=headers)
        assert response.status_code == 403
    
    def test_task_ownership_validation(self, client, test_users, test_resources):
        """Test task ownership (assignee) is properly validated"""
        # Assignee can update
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.put("/tasks/1", json={"title": "Assignee Update"}, headers=headers)
        assert response.status_code == 200
        
        # Non-assignee cannot update (without admin permission)
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.put("/tasks/1", json={"title": "Non-assignee Update"}, headers=headers)
        assert response.status_code == 403
    
    def test_admin_bypass_ownership(self, client, test_users, test_resources):
        """Test admin can bypass ownership restrictions"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        # Admin can update any document
        response = client.put("/documents/3", json={"title": "Admin Update"}, headers=headers)
        assert response.status_code == 200
        
        # Admin can update any project
        response = client.put("/projects/3", json={"name": "Admin Update"}, headers=headers)
        assert response.status_code == 200
        
        # Admin can update any task
        response = client.put("/tasks/2", json={"title": "Admin Update"}, headers=headers)
        assert response.status_code == 200
    
    def test_ownership_with_nonexistent_resource(self, client, test_users):
        """Test ownership validation with non-existent resources"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        # Try to update non-existent document
        response = client.put("/documents/999", json={"title": "Update"}, headers=headers)
        assert response.status_code == 404
        
        # Try to update non-existent project
        response = client.put("/projects/999", json={"name": "Update"}, headers=headers)
        assert response.status_code == 404
        
        # Try to update non-existent task
        response = client.put("/tasks/999", json={"title": "Update"}, headers=headers)
        assert response.status_code == 404


class TestErrorHandlingIntegration:
    """Tests error handling and response formatting.
    
    Validates: Proper error responses, status codes, error messages
    """
    
    def test_404_errors(self, client, test_users):
        """Test 404 error handling for non-existent resources"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        endpoints = [
            "/users/999",
            "/documents/999", 
            "/projects/999",
            "/tasks/999"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=headers)
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    def test_403_errors(self, client, test_users, test_resources):
        """Test 403 error handling for insufficient permissions"""
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        
        # Try operations that viewer doesn't have permission for
        operations = [
            ("POST", "/users/", {"email": "test@test.com", "name": "Test", "role": "user"}),
            ("PUT", "/users/1", {"name": "Update"}),
            ("DELETE", "/users/1", None),
            ("POST", "/documents/", {"title": "Test Doc"}),
        ]
        
        for method, endpoint, data in operations:
            if method == "POST":
                response = client.post(endpoint, json=data, headers=headers)
            elif method == "PUT":
                response = client.put(endpoint, json=data, headers=headers)
            elif method == "DELETE":
                response = client.delete(endpoint, headers=headers)
            
            assert response.status_code == 403
    
    def test_400_errors(self, client, test_users):
        """Test 400 error handling for bad requests"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        # Invalid role
        response = client.post("/users/", json={
            "email": "test@test.com",
            "name": "Test",
            "role": "invalid_role"
        }, headers=headers)
        assert response.status_code == 400
        
        # Duplicate email
        response = client.post("/users/", json={
            "email": "admin@test.com",  # Already exists
            "name": "Test",
            "role": "user"
        }, headers=headers)
        assert response.status_code == 400
    
    def test_401_errors(self, client):
        """Test 401 error handling for authentication failures"""
        # No token
        response = client.get("/users/")
        assert response.status_code == 401
        
        # Invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/users/", headers=headers)
        assert response.status_code == 401
    
    def test_validation_errors(self, client, test_users):
        """Test validation error handling"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        # Missing required fields
        response = client.post("/users/", json={}, headers=headers)
        assert response.status_code == 422  # Validation error
        
        # Invalid email format
        response = client.post("/users/", json={
            "email": "invalid-email",
            "name": "Test",
            "role": "user"
        }, headers=headers)
        assert response.status_code == 422


class TestCrossResourceIntegration:
    """Tests interactions between different resource types.
    
    Validates: Cross-resource relationships, cascading operations, complex scenarios
    """
    
    def test_project_task_relationship(self, client, test_users, test_resources):
        """Test project-task relationship and access control"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        # Create task in user's project
        task_data = {
            "title": "Project Task",
            "project_id": 1,  # User's public project
        }
        response = client.post("/tasks/", json=task_data, headers=headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        # Verify task appears in project's task list
        response = client.get("/projects/1/tasks", headers=headers)
        assert response.status_code == 200
        tasks = response.json()
        task_ids = [task["id"] for task in tasks]
        assert task_id in task_ids
    
    def test_user_resource_ownership_cascade(self, client, test_users, test_resources):
        """Test user ownership across multiple resource types"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        # User should see their own resources
        response = client.get("/documents/my/documents", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] > 0
        
        response = client.get("/projects/my/projects", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] > 0
        
        response = client.get("/tasks/my/tasks", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] > 0
    
    def test_admin_global_access(self, client, test_users, test_resources):
        """Test admin has global access to all resources"""
        headers = get_auth_headers(test_users["tokens"]["admin"])
        
        # Admin can access all resources
        endpoints = [
            "/users/",
            "/documents/?include_private=true",
            "/projects/?include_private=true", 
            "/tasks/"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] > 0 or len(data.get("users", [])) > 0
    
    def test_role_hierarchy_permissions(self, client, test_users, test_resources):
        """Test role hierarchy and permission inheritance"""
        # Test different roles have appropriate access levels
        
        # Viewer - read only
        headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.get("/documents/1", headers=headers)  # Public doc
        assert response.status_code == 200
        
        response = client.post("/documents/", json={"title": "Test"}, headers=headers)
        assert response.status_code == 403  # Cannot create
        
        # User - can create and manage own resources
        headers = get_auth_headers(test_users["tokens"]["user"])
        response = client.post("/documents/", json={"title": "User Doc"}, headers=headers)
        assert response.status_code == 201
        
        # Manager - broader permissions
        headers = get_auth_headers(test_users["tokens"]["manager"])
        response = client.get("/users/", headers=headers)
        assert response.status_code == 200  # Can read users
        
        # Admin - full access
        headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.post("/users/", json={
            "email": "admin_created@test.com",
            "name": "Admin Created",
            "role": "user"
        }, headers=headers)
        assert response.status_code == 201  # Can create users
    
    def test_complex_authorization_scenario(self, client, test_users, test_resources):
        """Test complex multi-resource authorization scenario"""
        headers = get_auth_headers(test_users["tokens"]["user"])
        
        # Create a private project
        project_data = {
            "name": "Private Project",
            "is_public": False
        }
        response = client.post("/projects/", json=project_data, headers=headers)
        assert response.status_code == 201
        project_id = response.json()["id"]
        
        # Create a task in the private project
        task_data = {
            "title": "Private Task",
            "project_id": project_id
        }
        response = client.post("/tasks/", json=task_data, headers=headers)
        assert response.status_code == 201
        task_id = response.json()["id"]
        
        # Verify other users cannot access the task
        other_headers = get_auth_headers(test_users["tokens"]["viewer"])
        response = client.get(f"/tasks/{task_id}", headers=other_headers)
        assert response.status_code == 403
        
        # But admin can access it
        admin_headers = get_auth_headers(test_users["tokens"]["admin"])
        response = client.get(f"/tasks/{task_id}", headers=admin_headers)
        assert response.status_code == 200