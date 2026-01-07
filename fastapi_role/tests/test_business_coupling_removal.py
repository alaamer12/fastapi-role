"""Comprehensive tests for business coupling removal.

This module provides thorough testing to ensure the RBAC system works
without any business dependencies and with arbitrary resource types.

Test Classes:
    TestNoDatabaseDependencies: Tests system works without database
    TestArbitraryResourceTypes: Tests with various resource types
    TestDifferentUserModels: Tests with different user model protocols
    TestVariousRoleConfigurations: Tests with different role setups
    TestCrossDomainCompatibility: Tests across different business domains
    TestNoHardcodedConcepts: Tests no hardcoded business concepts remain
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Protocol

import pytest
from fastapi import HTTPException

from fastapi_role import (
    Permission, 
    Privilege, 
    ResourceOwnership, 
    require,
    set_rbac_service,
    rbac_service_context,
)
from fastapi_role.core.roles import create_roles


class TestNoDatabaseDependencies:
    """Tests that system works without any database dependencies.
    
    Validates: Requirements 9.3
    """

    def test_no_database_imports(self):
        """Test that RBAC core has no database imports."""
        
        import fastapi_role.rbac_service as rbac_service_module
        import fastapi_role.rbac as rbac_module
        import fastapi_role.core.roles as roles_module
        
        # Check module source for database-related imports
        modules_to_check = [rbac_service_module, rbac_module, roles_module]
        
        for module in modules_to_check:
            module_source = inspect.getsource(module)
            
            # Should not import database-related modules (check import statements only)
            import_lines = [line.strip().lower() for line in module_source.split('\n') 
                          if line.strip().startswith(('import ', 'from '))]
            
            database_imports = [
                "sqlalchemy", "django", "peewee", "tortoise",
                "pymongo", "redis", "sqlite", "psycopg",
                "mysql", "baseservice"
            ]
            
            for import_line in import_lines:
                for db_import in database_imports:
                    assert db_import not in import_line, f"Found database import '{db_import}' in {module.__name__}: {import_line}"

    def test_rbac_service_no_database_inheritance(self):
        """Test that RBACService doesn't inherit from database classes."""
        
        from fastapi_role.rbac_service import RBACService
        
        # Check class hierarchy
        mro = RBACService.__mro__
        class_names = [cls.__name__ for cls in mro]
        
        # Should not inherit from database-related base classes
        database_base_classes = [
            "BaseService", "Model", "Document", "Entity",
            "DatabaseService", "SessionMixin"
        ]
        
        for base_class in database_base_classes:
            assert base_class not in class_names, f"RBACService inherits from database class: {base_class}"

    @pytest.mark.asyncio
    async def test_memory_only_rbac_service(self):
        """Test RBAC service works with memory-only implementation."""
        
        class MemoryRBACService:
            """Pure memory-based RBAC service with no database dependencies."""
            
            def __init__(self):
                self.permissions = {
                    ("user@example.com", "documents", "read"): True,
                    ("user@example.com", "documents", "write"): False,
                    ("admin@example.com", "documents", "read"): True,
                    ("admin@example.com", "documents", "write"): True,
                }
                self.ownership = {
                    ("user@example.com", "document", "123"): True,
                    ("user@example.com", "document", "456"): False,
                }
            
            async def check_permission(self, user, resource, action, context=None):
                key = (user.email, resource, action)
                return self.permissions.get(key, False)
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                key = (user.email, resource_type, str(resource_id))
                return self.ownership.get(key, False)

        # Create user without database model
        class SimpleUser:
            def __init__(self, email: str, role: str):
                self.email = email
                self.role = role

        user = SimpleUser("user@example.com", "user")
        rbac_service = MemoryRBACService()
        
        @require(Permission("documents", "read"))
        async def read_document(current_user: SimpleUser, rbac_service: MemoryRBACService):
            return f"document_read_by_{current_user.email}"

        result = await read_document(user, rbac_service)
        assert result == "document_read_by_user@example.com"

    def test_no_session_management_in_core(self):
        """Test that RBAC core doesn't manage database sessions."""
        
        from fastapi_role.rbac_service import RBACService
        
        # Check RBACService methods
        rbac_methods = [method for method in dir(RBACService) if not method.startswith('_')]
        
        # Should not have session management methods
        session_methods = [
            "get_session", "create_session", "close_session",
            "commit", "rollback", "begin_transaction"
        ]
        
        for session_method in session_methods:
            assert session_method not in rbac_methods, f"RBACService has session method: {session_method}"

    @pytest.mark.asyncio
    async def test_file_based_rbac_service(self):
        """Test RBAC service works with file-based configuration."""
        
        class FileBasedRBACService:
            """File-based RBAC service with no database."""
            
            def __init__(self, config_data: Dict[str, Any]):
                self.config = config_data
            
            async def check_permission(self, user, resource, action, context=None):
                user_permissions = self.config.get("permissions", {}).get(user.email, [])
                return f"{resource}:{action}" in user_permissions
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                user_resources = self.config.get("ownership", {}).get(user.email, {})
                owned_resources = user_resources.get(resource_type, [])
                return str(resource_id) in owned_resources

        # Configuration without database
        config = {
            "permissions": {
                "user@example.com": ["files:read", "files:write"],
                "admin@example.com": ["files:read", "files:write", "files:delete"]
            },
            "ownership": {
                "user@example.com": {"file": ["1", "2", "3"]},
                "admin@example.com": {"file": ["1", "2", "3", "4", "5"]}
            }
        }
        
        class ConfigUser:
            def __init__(self, email: str):
                self.email = email

        user = ConfigUser("user@example.com")
        rbac_service = FileBasedRBACService(config)
        
        @require(Permission("files", "read"), ResourceOwnership("file"))
        async def read_file(file_id: str, current_user: ConfigUser, rbac_service: FileBasedRBACService):
            return f"file_{file_id}_read_by_{current_user.email}"

        result = await read_file("1", user, rbac_service)
        assert result == "file_1_read_by_user@example.com"


class TestArbitraryResourceTypes:
    """Tests system works with arbitrary resource types.
    
    Validates: Requirements 9.3
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a flexible RBAC service."""
        
        class FlexibleRBACService:
            async def check_permission(self, user, resource, action, context=None):
                # Allow all permissions for testing
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                # Allow all ownership for testing
                return True
        
        return FlexibleRBACService()

    @pytest.fixture
    def user(self):
        """Create a generic user."""
        
        class GenericUser:
            def __init__(self):
                self.email = "user@example.com"
                self.role = "user"
        
        return GenericUser()

    @pytest.mark.asyncio
    async def test_document_management_resources(self, user, rbac_service):
        """Test with document management resource types."""
        
        @require(Permission("documents", "create"))
        async def create_document(title: str, current_user, rbac_service):
            return f"document_{title}_created_by_{current_user.email}"
        
        @require(Permission("folders", "organize"))
        async def organize_folder(folder_name: str, current_user, rbac_service):
            return f"folder_{folder_name}_organized_by_{current_user.email}"
        
        @require(Permission("templates", "use"))
        async def use_template(template_id: str, current_user, rbac_service):
            return f"template_{template_id}_used_by_{current_user.email}"

        doc_result = await create_document("report", user, rbac_service)
        folder_result = await organize_folder("projects", user, rbac_service)
        template_result = await use_template("invoice", user, rbac_service)
        
        assert "document_report_created" in doc_result
        assert "folder_projects_organized" in folder_result
        assert "template_invoice_used" in template_result

    @pytest.mark.asyncio
    async def test_project_management_resources(self, user, rbac_service):
        """Test with project management resource types."""
        
        @require(Permission("projects", "manage"))
        async def manage_project(project_id: str, current_user, rbac_service):
            return f"project_{project_id}_managed_by_{current_user.email}"
        
        @require(Permission("tasks", "assign"))
        async def assign_task(task_id: str, assignee: str, current_user, rbac_service):
            return f"task_{task_id}_assigned_to_{assignee}_by_{current_user.email}"
        
        @require(Permission("milestones", "track"))
        async def track_milestone(milestone_id: str, current_user, rbac_service):
            return f"milestone_{milestone_id}_tracked_by_{current_user.email}"

        project_result = await manage_project("proj_123", user, rbac_service)
        task_result = await assign_task("task_456", "developer", user, rbac_service)
        milestone_result = await track_milestone("mile_789", user, rbac_service)
        
        assert "project_proj_123_managed" in project_result
        assert "task_456_assigned_to_developer" in task_result
        assert "milestone_mile_789_tracked" in milestone_result

    @pytest.mark.asyncio
    async def test_content_management_resources(self, user, rbac_service):
        """Test with content management resource types."""
        
        @require(Permission("articles", "publish"))
        async def publish_article(article_id: str, current_user, rbac_service):
            return f"article_{article_id}_published_by_{current_user.email}"
        
        @require(Permission("media", "upload"))
        async def upload_media(media_type: str, current_user, rbac_service):
            return f"media_{media_type}_uploaded_by_{current_user.email}"
        
        @require(Permission("categories", "manage"))
        async def manage_category(category_name: str, current_user, rbac_service):
            return f"category_{category_name}_managed_by_{current_user.email}"

        article_result = await publish_article("art_123", user, rbac_service)
        media_result = await upload_media("image", user, rbac_service)
        category_result = await manage_category("news", user, rbac_service)
        
        assert "article_art_123_published" in article_result
        assert "media_image_uploaded" in media_result
        assert "category_news_managed" in category_result

    @pytest.mark.asyncio
    async def test_scientific_research_resources(self, user, rbac_service):
        """Test with scientific research resource types."""
        
        @require(Permission("experiments", "conduct"))
        async def conduct_experiment(experiment_id: str, current_user, rbac_service):
            return f"experiment_{experiment_id}_conducted_by_{current_user.email}"
        
        @require(Permission("datasets", "analyze"))
        async def analyze_dataset(dataset_id: str, current_user, rbac_service):
            return f"dataset_{dataset_id}_analyzed_by_{current_user.email}"
        
        @require(Permission("publications", "submit"))
        async def submit_publication(paper_title: str, current_user, rbac_service):
            return f"paper_{paper_title}_submitted_by_{current_user.email}"

        experiment_result = await conduct_experiment("exp_123", user, rbac_service)
        dataset_result = await analyze_dataset("data_456", user, rbac_service)
        publication_result = await submit_publication("research_paper", user, rbac_service)
        
        assert "experiment_exp_123_conducted" in experiment_result
        assert "dataset_data_456_analyzed" in dataset_result
        assert "paper_research_paper_submitted" in publication_result

    @pytest.mark.asyncio
    async def test_gaming_platform_resources(self, user, rbac_service):
        """Test with gaming platform resource types."""
        
        @require(Permission("games", "launch"))
        async def launch_game(game_id: str, current_user, rbac_service):
            return f"game_{game_id}_launched_by_{current_user.email}"
        
        @require(Permission("tournaments", "organize"))
        async def organize_tournament(tournament_name: str, current_user, rbac_service):
            return f"tournament_{tournament_name}_organized_by_{current_user.email}"
        
        @require(Permission("achievements", "award"))
        async def award_achievement(achievement_id: str, player: str, current_user, rbac_service):
            return f"achievement_{achievement_id}_awarded_to_{player}_by_{current_user.email}"

        game_result = await launch_game("game_123", user, rbac_service)
        tournament_result = await organize_tournament("championship", user, rbac_service)
        achievement_result = await award_achievement("winner", "player1", user, rbac_service)
        
        assert "game_game_123_launched" in game_result
        assert "tournament_championship_organized" in tournament_result
        assert "achievement_winner_awarded_to_player1" in achievement_result

    @pytest.mark.asyncio
    async def test_custom_resource_ownership(self, user, rbac_service):
        """Test resource ownership with arbitrary resource types."""
        
        @require(ResourceOwnership("artwork"))
        async def modify_artwork(artwork_id: str, current_user, rbac_service):
            return f"artwork_{artwork_id}_modified_by_{current_user.email}"
        
        @require(ResourceOwnership("recipe"))
        async def edit_recipe(recipe_id: str, current_user, rbac_service):
            return f"recipe_{recipe_id}_edited_by_{current_user.email}"
        
        @require(ResourceOwnership("playlist"))
        async def update_playlist(playlist_id: str, current_user, rbac_service):
            return f"playlist_{playlist_id}_updated_by_{current_user.email}"

        artwork_result = await modify_artwork("art_123", user, rbac_service)
        recipe_result = await edit_recipe("recipe_456", user, rbac_service)
        playlist_result = await update_playlist("playlist_789", user, rbac_service)
        
        assert "artwork_art_123_modified" in artwork_result
        assert "recipe_recipe_456_edited" in recipe_result
        assert "playlist_playlist_789_updated" in playlist_result


class TestDifferentUserModels:
    """Tests system works with different user models and protocols.
    
    Validates: Requirements 9.3
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a flexible RBAC service."""
        
        class FlexibleRBACService:
            async def check_permission(self, user, resource, action, context=None):
                return hasattr(user, 'email') and user.email.endswith('@example.com')
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return hasattr(user, 'id') and user.id is not None
        
        return FlexibleRBACService()

    @pytest.mark.asyncio
    async def test_minimal_user_protocol(self, rbac_service):
        """Test with minimal user protocol."""
        
        class MinimalUser:
            def __init__(self, email: str):
                self.email = email
        
        user = MinimalUser("minimal@example.com")
        
        @require(Permission("minimal", "test"))
        async def minimal_function(current_user: MinimalUser, rbac_service):
            return f"minimal_access_for_{current_user.email}"

        result = await minimal_function(user, rbac_service)
        assert result == "minimal_access_for_minimal@example.com"

    @pytest.mark.asyncio
    async def test_rich_user_model(self, rbac_service):
        """Test with rich user model with many attributes."""
        
        class RichUser:
            def __init__(self, user_id: int, email: str, name: str, role: str):
                self.id = user_id
                self.email = email
                self.name = name
                self.role = role
                self.permissions = []
                self.groups = []
                self.metadata = {}
                self.created_at = "2024-01-01"
                self.last_login = "2024-01-07"
        
        user = RichUser(1, "rich@example.com", "Rich User", "admin")
        
        @require(Permission("rich", "test"))
        async def rich_function(current_user: RichUser, rbac_service):
            return f"rich_access_for_{current_user.name}_{current_user.email}"

        result = await rich_function(user, rbac_service)
        assert result == "rich_access_for_Rich User_rich@example.com"

    @pytest.mark.asyncio
    async def test_dictionary_user_model(self, rbac_service):
        """Test with dictionary-based user model."""
        
        class DictUser:
            def __init__(self, user_data: Dict[str, Any]):
                self.data = user_data
            
            @property
            def email(self):
                return self.data.get('email')
            
            @property
            def id(self):
                return self.data.get('id')
            
            @property
            def role(self):
                return self.data.get('role')
        
        user_data = {
            'id': 123,
            'email': 'dict@example.com',
            'role': 'user',
            'department': 'engineering',
            'level': 'senior'
        }
        user = DictUser(user_data)
        
        @require(Permission("dict", "test"))
        async def dict_function(current_user: DictUser, rbac_service):
            return f"dict_access_for_{current_user.email}"

        result = await dict_function(user, rbac_service)
        assert result == "dict_access_for_dict@example.com"

    @pytest.mark.asyncio
    async def test_protocol_based_user(self, rbac_service):
        """Test with protocol-based user interface."""
        
        class UserProtocol(Protocol):
            email: str
            id: Optional[int]
        
        class ProtocolUser:
            def __init__(self, email: str, user_id: int):
                self.email = email
                self.id = user_id
        
        user = ProtocolUser("protocol@example.com", 456)
        
        @require(Permission("protocol", "test"))
        async def protocol_function(current_user: UserProtocol, rbac_service):
            return f"protocol_access_for_{current_user.email}"

        result = await protocol_function(user, rbac_service)
        assert result == "protocol_access_for_protocol@example.com"

    @pytest.mark.asyncio
    async def test_custom_attribute_user(self, rbac_service):
        """Test with user having custom attributes."""
        
        class CustomUser:
            def __init__(self):
                self.email = "custom@example.com"
                self.id = 789
                self.tenant_id = "tenant_123"
                self.organization = "ACME Corp"
                self.security_clearance = "level_3"
                self.api_key = "key_abc123"
        
        user = CustomUser()
        
        @require(Permission("custom", "test"))
        async def custom_function(current_user: CustomUser, rbac_service):
            return f"custom_access_for_{current_user.organization}_{current_user.email}"

        result = await custom_function(user, rbac_service)
        assert result == "custom_access_for_ACME Corp_custom@example.com"

    @pytest.mark.asyncio
    async def test_jwt_token_user(self, rbac_service):
        """Test with JWT token-based user."""
        
        class JWTUser:
            def __init__(self, token_payload: Dict[str, Any]):
                self.payload = token_payload
            
            @property
            def email(self):
                return self.payload.get('email')
            
            @property
            def id(self):
                return self.payload.get('sub')
            
            @property
            def role(self):
                return self.payload.get('role')
            
            @property
            def scopes(self):
                return self.payload.get('scopes', [])
        
        token_payload = {
            'sub': 'user_999',
            'email': 'jwt@example.com',
            'role': 'api_user',
            'scopes': ['read', 'write'],
            'iss': 'auth_service',
            'exp': 1704672000
        }
        user = JWTUser(token_payload)
        
        @require(Permission("jwt", "test"))
        async def jwt_function(current_user: JWTUser, rbac_service):
            return f"jwt_access_for_{current_user.email}_with_scopes_{len(current_user.scopes)}"

        result = await jwt_function(user, rbac_service)
        assert result == "jwt_access_for_jwt@example.com_with_scopes_2"


class TestVariousRoleConfigurations:
    """Tests system works with various role configurations.
    
    Validates: Requirements 9.3
    """

    @pytest.fixture
    def rbac_service(self):
        """Create a role-aware RBAC service."""
        
        class RoleAwareRBACService:
            def __init__(self):
                self.role_permissions = {}
            
            def set_role_permissions(self, role_permissions: Dict[str, List[str]]):
                self.role_permissions = role_permissions
            
            async def check_permission(self, user, resource, action, context=None):
                user_role = getattr(user, 'role', None)
                if not user_role:
                    return False
                
                allowed_permissions = self.role_permissions.get(user_role, [])
                return f"{resource}:{action}" in allowed_permissions
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True  # Allow all ownership for testing
        
        return RoleAwareRBACService()

    @pytest.mark.asyncio
    async def test_flat_role_configuration(self, rbac_service):
        """Test with flat role configuration."""
        
        # Create flat roles
        FlatRole = create_roles(["viewer", "editor", "admin"])
        
        rbac_service.set_role_permissions({
            "viewer": ["documents:read", "reports:view"],
            "editor": ["documents:read", "documents:write", "reports:view"],
            "admin": ["documents:read", "documents:write", "documents:delete", "reports:view", "reports:create"]
        })
        
        class FlatUser:
            def __init__(self, email: str, role: str):
                self.email = email
                self.role = role
        
        viewer = FlatUser("viewer@example.com", "viewer")
        editor = FlatUser("editor@example.com", "editor")
        
        @require(FlatRole.VIEWER)
        async def view_document(current_user: FlatUser, rbac_service):
            return f"document_viewed_by_{current_user.role}"
        
        @require(FlatRole.EDITOR)
        async def edit_document(current_user: FlatUser, rbac_service):
            return f"document_edited_by_{current_user.role}"

        view_result = await view_document(viewer, rbac_service)
        edit_result = await edit_document(editor, rbac_service)
        
        assert view_result == "document_viewed_by_viewer"
        assert edit_result == "document_edited_by_editor"

    @pytest.mark.asyncio
    async def test_hierarchical_role_configuration(self, rbac_service):
        """Test with hierarchical role configuration."""
        
        # Create hierarchical roles
        HierarchicalRole = create_roles(["intern", "junior", "senior", "lead", "director"])
        
        rbac_service.set_role_permissions({
            "intern": ["tasks:view"],
            "junior": ["tasks:view", "tasks:create"],
            "senior": ["tasks:view", "tasks:create", "tasks:assign"],
            "lead": ["tasks:view", "tasks:create", "tasks:assign", "projects:manage"],
            "director": ["tasks:view", "tasks:create", "tasks:assign", "projects:manage", "budget:approve"]
        })
        
        class HierarchicalUser:
            def __init__(self, email: str, role: str):
                self.email = email
                self.role = role
        
        senior = HierarchicalUser("senior@example.com", "senior")
        lead = HierarchicalUser("lead@example.com", "lead")
        
        @require(HierarchicalRole.SENIOR)
        async def assign_task(current_user: HierarchicalUser, rbac_service):
            return f"task_assigned_by_{current_user.role}"
        
        @require(HierarchicalRole.LEAD)
        async def manage_project(current_user: HierarchicalUser, rbac_service):
            return f"project_managed_by_{current_user.role}"

        assign_result = await assign_task(senior, rbac_service)
        manage_result = await manage_project(lead, rbac_service)
        
        assert assign_result == "task_assigned_by_senior"
        assert manage_result == "project_managed_by_lead"

    @pytest.mark.asyncio
    async def test_domain_specific_roles(self, rbac_service):
        """Test with domain-specific role configurations."""
        
        # Healthcare domain roles
        HealthcareRole = create_roles(["patient", "nurse", "doctor", "admin"])
        
        # Education domain roles  
        EducationRole = create_roles(["student", "teacher", "principal", "superintendent"])
        
        rbac_service.set_role_permissions({
            "doctor": ["patients:access", "prescriptions:write"],
            "teacher": ["students:grade", "curriculum:access"],
        })
        
        class DomainUser:
            def __init__(self, email: str, role: str, domain: str):
                self.email = email
                self.role = role
                self.domain = domain
        
        doctor = DomainUser("doctor@hospital.com", "doctor", "healthcare")
        teacher = DomainUser("teacher@school.edu", "teacher", "education")
        
        @require(HealthcareRole.DOCTOR)
        async def access_patient(current_user: DomainUser, rbac_service):
            return f"patient_accessed_by_{current_user.role}_in_{current_user.domain}"
        
        @require(EducationRole.TEACHER)
        async def grade_student(current_user: DomainUser, rbac_service):
            return f"student_graded_by_{current_user.role}_in_{current_user.domain}"

        patient_result = await access_patient(doctor, rbac_service)
        grade_result = await grade_student(teacher, rbac_service)
        
        assert patient_result == "patient_accessed_by_doctor_in_healthcare"
        assert grade_result == "student_graded_by_teacher_in_education"

    @pytest.mark.asyncio
    async def test_multi_tenant_roles(self, rbac_service):
        """Test with multi-tenant role configurations."""
        
        # Tenant-specific roles
        TenantRole = create_roles(["tenant_user", "tenant_admin", "super_admin"])
        
        rbac_service.set_role_permissions({
            "tenant_user": ["tenant_data:read"],
            "tenant_admin": ["tenant_data:read", "tenant_data:write", "tenant_users:manage"],
            "super_admin": ["all:access"]
        })
        
        class TenantUser:
            def __init__(self, email: str, role: str, tenant_id: str):
                self.email = email
                self.role = role
                self.tenant_id = tenant_id
        
        tenant_admin = TenantUser("admin@tenant1.com", "tenant_admin", "tenant_1")
        super_admin = TenantUser("super@platform.com", "super_admin", "platform")
        
        @require(TenantRole.TENANT_ADMIN)
        async def manage_tenant_users(current_user: TenantUser, rbac_service):
            return f"users_managed_in_{current_user.tenant_id}_by_{current_user.role}"
        
        @require(TenantRole.SUPER_ADMIN)
        async def platform_operation(current_user: TenantUser, rbac_service):
            return f"platform_operation_by_{current_user.role}"

        tenant_result = await manage_tenant_users(tenant_admin, rbac_service)
        platform_result = await platform_operation(super_admin, rbac_service)
        
        assert tenant_result == "users_managed_in_tenant_1_by_tenant_admin"
        assert platform_result == "platform_operation_by_super_admin"


class TestCrossDomainCompatibility:
    """Tests system works across different business domains.
    
    Validates: Requirements 9.3
    """

    @pytest.fixture
    def universal_rbac_service(self):
        """Create a universal RBAC service that works across domains."""
        
        class UniversalRBACService:
            async def check_permission(self, user, resource, action, context=None):
                # Universal permission logic
                return hasattr(user, 'email') and '@' in user.email
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                # Universal ownership logic
                return hasattr(user, 'id') and user.id is not None
        
        return UniversalRBACService()

    @pytest.mark.asyncio
    async def test_ecommerce_domain(self, universal_rbac_service):
        """Test RBAC system in e-commerce domain."""
        
        ECommerceRole = create_roles(["customer", "vendor", "marketplace_admin"])
        
        class ECommerceUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
        
        customer = ECommerceUser(1, "customer@shop.com", "customer")
        
        @require(Permission("products", "browse"))
        async def browse_products(current_user: ECommerceUser, rbac_service):
            return f"products_browsed_by_{current_user.email}"
        
        @require(Permission("orders", "place"))
        async def place_order(current_user: ECommerceUser, rbac_service):
            return f"order_placed_by_{current_user.email}"

        browse_result = await browse_products(customer, universal_rbac_service)
        order_result = await place_order(customer, universal_rbac_service)
        
        assert browse_result == "products_browsed_by_customer@shop.com"
        assert order_result == "order_placed_by_customer@shop.com"

    @pytest.mark.asyncio
    async def test_saas_platform_domain(self, universal_rbac_service):
        """Test RBAC system in SaaS platform domain."""
        
        SaaSRole = create_roles(["trial_user", "paid_user", "enterprise_user", "platform_admin"])
        
        class SaaSUser:
            def __init__(self, user_id: int, email: str, role: str, subscription: str):
                self.id = user_id
                self.email = email
                self.role = role
                self.subscription = subscription
        
        paid_user = SaaSUser(2, "user@company.com", "paid_user", "professional")
        
        @require(Permission("workspaces", "create"))
        async def create_workspace(current_user: SaaSUser, rbac_service):
            return f"workspace_created_by_{current_user.email}_on_{current_user.subscription}"
        
        @require(Permission("integrations", "configure"))
        async def configure_integration(current_user: SaaSUser, rbac_service):
            return f"integration_configured_by_{current_user.email}"

        workspace_result = await create_workspace(paid_user, universal_rbac_service)
        integration_result = await configure_integration(paid_user, universal_rbac_service)
        
        assert workspace_result == "workspace_created_by_user@company.com_on_professional"
        assert integration_result == "integration_configured_by_user@company.com"

    @pytest.mark.asyncio
    async def test_content_management_domain(self, universal_rbac_service):
        """Test RBAC system in content management domain."""
        
        CMSRole = create_roles(["contributor", "editor", "publisher", "admin"])
        
        class CMSUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
        
        editor = CMSUser(3, "editor@cms.com", "editor")
        
        @require(Permission("articles", "edit"))
        async def edit_article(current_user: CMSUser, rbac_service):
            return f"article_edited_by_{current_user.email}"
        
        @require(Permission("media", "manage"))
        async def manage_media(current_user: CMSUser, rbac_service):
            return f"media_managed_by_{current_user.email}"

        article_result = await edit_article(editor, universal_rbac_service)
        media_result = await manage_media(editor, universal_rbac_service)
        
        assert article_result == "article_edited_by_editor@cms.com"
        assert media_result == "media_managed_by_editor@cms.com"

    @pytest.mark.asyncio
    async def test_iot_platform_domain(self, universal_rbac_service):
        """Test RBAC system in IoT platform domain."""
        
        IoTRole = create_roles(["device_owner", "fleet_manager", "platform_operator"])
        
        class IoTUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
        
        fleet_manager = IoTUser(4, "manager@iot.com", "fleet_manager")
        
        @require(Permission("devices", "monitor"))
        async def monitor_devices(current_user: IoTUser, rbac_service):
            return f"devices_monitored_by_{current_user.email}"
        
        @require(Permission("telemetry", "analyze"))
        async def analyze_telemetry(current_user: IoTUser, rbac_service):
            return f"telemetry_analyzed_by_{current_user.email}"

        monitor_result = await monitor_devices(fleet_manager, universal_rbac_service)
        telemetry_result = await analyze_telemetry(fleet_manager, universal_rbac_service)
        
        assert monitor_result == "devices_monitored_by_manager@iot.com"
        assert telemetry_result == "telemetry_analyzed_by_manager@iot.com"


class TestNoHardcodedConcepts:
    """Tests that no hardcoded business concepts remain in any code path.
    
    Validates: Requirements 9.3
    """

    def test_no_hardcoded_business_terms_in_core(self):
        """Test that core RBAC modules have no hardcoded business terms."""
        
        import fastapi_role.rbac_service as rbac_service_module
        import fastapi_role.rbac as rbac_module
        import fastapi_role.core.roles as roles_module
        
        modules_to_check = [rbac_service_module, rbac_module, roles_module]
        
        # Business terms that should not appear in core RBAC code
        business_terms = [
            "customer", "salesman", "quote", "order", "invoice",
            "product", "inventory", "shipping", "billing", "payment",
            "crm", "sales", "marketing", "finance", "accounting"
        ]
        
        for module in modules_to_check:
            module_source = inspect.getsource(module).lower()
            
            for term in business_terms:
                assert term not in module_source, f"Found hardcoded business term '{term}' in {module.__name__}"

    def test_no_hardcoded_role_names(self):
        """Test that no hardcoded role names exist in core code."""
        
        from fastapi_role.rbac_service import RBACService
        from fastapi_role import rbac
        
        # Get source code
        rbac_service_source = inspect.getsource(RBACService).lower()
        rbac_source = inspect.getsource(rbac).lower()
        
        # Hardcoded role names that should not appear
        hardcoded_roles = [
            '"customer"', "'customer'",
            '"salesman"', "'salesman'", 
            '"superadmin"', "'superadmin'",
            '"admin"', "'admin'"
        ]
        
        sources = [
            (rbac_service_source, "RBACService"),
            (rbac_source, "rbac module")
        ]
        
        for source, module_name in sources:
            for role in hardcoded_roles:
                assert role not in source, f"Found hardcoded role {role} in {module_name}"

    def test_no_hardcoded_resource_types(self):
        """Test that no hardcoded resource types exist in core code."""
        
        import fastapi_role.rbac_service as rbac_service_module
        
        rbac_service_source = inspect.getsource(rbac_service_module).lower()
        
        # Hardcoded resource types that should not appear
        hardcoded_resources = [
            '"customer"', "'customer'",
            '"order"', "'order'",
            '"quote"', "'quote'",
            '"invoice"', "'invoice'"
        ]
        
        for resource in hardcoded_resources:
            assert resource not in rbac_service_source, f"Found hardcoded resource type {resource} in RBACService"

    def test_no_hardcoded_permissions(self):
        """Test that no hardcoded permissions exist in core code."""
        
        from fastapi_role import rbac
        
        rbac_source = inspect.getsource(rbac).lower()
        
        # Hardcoded permissions that should not appear
        hardcoded_permissions = [
            '"create_quote"', "'create_quote'",
            '"view_customer"', "'view_customer'",
            '"manage_orders"', "'manage_orders'"
        ]
        
        for permission in hardcoded_permissions:
            assert permission not in rbac_source, f"Found hardcoded permission {permission} in rbac module"

    @pytest.mark.asyncio
    async def test_dynamic_resource_handling(self):
        """Test that system handles completely dynamic resources."""
        
        class DynamicRBACService:
            def __init__(self):
                self.allowed_resources = set()
            
            def allow_resource(self, resource_type: str):
                self.allowed_resources.add(resource_type)
            
            async def check_permission(self, user, resource, action, context=None):
                return resource in self.allowed_resources
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return resource_type in self.allowed_resources
        
        rbac_service = DynamicRBACService()
        
        class DynamicUser:
            def __init__(self):
                self.email = "dynamic@example.com"
                self.id = 1
        
        user = DynamicUser()
        
        # Test with completely arbitrary resource types
        arbitrary_resources = [
            "quantum_computers", "space_missions", "time_machines",
            "dragon_eggs", "magic_spells", "alien_artifacts"
        ]
        
        for resource in arbitrary_resources:
            rbac_service.allow_resource(resource)
            
            @require(Permission(resource, "access"))
            async def access_arbitrary_resource(
                current_user: DynamicUser, 
                rbac_service: DynamicRBACService,
                resource_name: str = resource
            ):
                return f"{resource_name}_accessed_by_{current_user.email}"
            
            result = await access_arbitrary_resource(user, rbac_service)
            assert result == f"{resource}_accessed_by_dynamic@example.com"

    def test_configurable_system_behavior(self):
        """Test that all system behavior is configurable, not hardcoded."""
        
        from fastapi_role.core.roles import create_roles
        
        # Test that roles can be completely arbitrary
        arbitrary_role_sets = [
            ["alpha", "beta", "gamma"],
            ["red", "green", "blue"],
            ["small", "medium", "large", "extra_large"],
            ["level_1", "level_2", "level_3", "level_4", "level_5"]
        ]
        
        for role_set in arbitrary_role_sets:
            # Should be able to create roles with any names
            CustomRole = create_roles(role_set)
            
            # Verify all roles were created
            for role_name in role_set:
                assert hasattr(CustomRole, role_name.upper())
                role_value = getattr(CustomRole, role_name.upper())
                assert role_value.value == role_name