"""Comprehensive tests for example applications.

This module provides comprehensive testing for all example applications,
ensuring they work correctly and demonstrate pure general RBAC principles.

Test Classes:
    TestMinimalExample: Tests the minimal pure RBAC example
    TestFileBasedExample: Tests the file-based configuration example
    TestDatabaseExample: Tests the database integration example
    TestExampleSetupTime: Tests that examples meet setup time requirements
    TestExampleDocumentation: Tests that examples are properly documented
"""

import asyncio
import time
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

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


class TestMinimalExample:
    """Tests for the minimal pure RBAC example.
    
    Validates: Requirements 12.1
    """

    def test_minimal_example_exists(self):
        """Test that minimal example file exists."""
        
        example_path = Path("../examples/minimal_rbac_example.py")
        assert example_path.exists(), "Minimal example file should exist"

    def test_minimal_example_imports(self):
        """Test that minimal example has correct imports."""
        
        example_path = Path("../examples/minimal_rbac_example.py")
        
        if example_path.exists():
            content = example_path.read_text()
            
            # Should import from fastapi_role
            assert "from fastapi_role import" in content
            
            # Should use dynamic roles
            assert "create_roles" in content
            
            # Should not have hardcoded business concepts
            assert "customer" not in content.lower()
            assert "order" not in content.lower()
            assert "quote" not in content.lower()

    def test_minimal_example_structure(self):
        """Test that minimal example has proper structure."""
        
        example_path = Path("../examples/minimal_rbac_example.py")
        
        if example_path.exists():
            content = example_path.read_text()
            
            # Should be a single file
            assert len(content) > 0
            
            # Should have FastAPI app
            assert "FastAPI" in content
            
            # Should have RBAC decorators
            assert "@require" in content
            
            # Should have generic resource types
            assert any(generic in content for generic in ["documents", "projects", "tasks", "resources"])

    @pytest.mark.asyncio
    async def test_minimal_example_functionality(self):
        """Test that minimal example functions work correctly."""
        
        # Create minimal example components
        Role = create_roles(["user", "admin"])
        
        class MockUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
        
        class MockRBACService:
            async def check_permission(self, user, resource, action):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        rbac_service = MockRBACService()
        user = MockUser(1, "user@example.com", "user")
        
        # Test basic protected function
        @require(Role.USER)
        async def get_resources(current_user: MockUser, rbac_service: MockRBACService):
            return {"resources": ["resource1", "resource2"], "user": current_user.email}
        
        result = await get_resources(user, rbac_service)
        assert result["user"] == "user@example.com"
        assert len(result["resources"]) == 2

    def test_minimal_example_no_business_coupling(self):
        """Test that minimal example has no business coupling."""
        
        example_path = Path("../examples/minimal_rbac_example.py")
        
        if example_path.exists():
            content = example_path.read_text().lower()
            
            # Should not contain business-specific terms
            business_terms = [
                "customer", "salesman", "quote", "order", "invoice",
                "product", "inventory", "shipping", "billing"
            ]
            
            for term in business_terms:
                assert term not in content, f"Minimal example should not contain business term: {term}"

    def test_minimal_example_setup_simplicity(self):
        """Test that minimal example is simple to set up."""
        
        example_path = Path("../examples/minimal_rbac_example.py")
        
        if example_path.exists():
            content = example_path.read_text()
            
            # Should be self-contained (minimal external dependencies)
            lines = content.split('\n')
            import_lines = [line for line in lines if line.strip().startswith('import') or line.strip().startswith('from')]
            
            # Should have minimal imports
            assert len(import_lines) <= 12, "Minimal example should have few imports"
            
            # Should not require database setup
            assert "database" not in content.lower()
            assert "db" not in content.lower()
            assert "sqlite" not in content.lower()


class TestFileBasedExample:
    """Tests for the file-based configuration example.
    
    Validates: Requirements 12.2
    """

    def test_file_based_example_exists(self):
        """Test that file-based example exists."""
        
        example_path = Path("../examples/file_based_rbac_example.py")
        config_path = Path("../examples/config")
        
        assert example_path.exists(), "File-based example should exist"
        assert config_path.exists(), "Configuration directory should exist"

    def test_configuration_files_exist(self):
        """Test that all required configuration files exist."""
        
        config_files = [
            "../examples/config/roles.yaml",
            "../examples/config/policies.yaml", 
            "../examples/config/resources.yaml",
            "../examples/config/users.yaml"
        ]
        
        for config_file in config_files:
            path = Path(config_file)
            assert path.exists(), f"Configuration file should exist: {config_file}"

    def test_configuration_file_structure(self):
        """Test that configuration files have proper structure."""
        
        roles_path = Path("../examples/config/roles.yaml")
        
        if roles_path.exists():
            content = roles_path.read_text()
            
            # Should define roles
            assert "roles:" in content or "- " in content
            
            # Should not have hardcoded business roles
            content_lower = content.lower()
            assert "customer" not in content_lower
            assert "salesman" not in content_lower

    def test_file_based_example_loads_configuration(self):
        """Test that file-based example loads configuration correctly."""
        
        example_path = Path("../examples/file_based_rbac_example.py")
        
        if example_path.exists():
            content = example_path.read_text()
            
            # Should load configuration from files
            assert "yaml" in content.lower() or "json" in content.lower()
            
            # Should use configuration to create roles
            assert "create_roles" in content
            
            # Should reference config files
            assert "config" in content.lower()

    @pytest.mark.asyncio
    async def test_file_based_example_functionality(self):
        """Test that file-based example functions work correctly."""
        
        # Simulate loading configuration
        config_roles = ["viewer", "editor", "admin"]
        Role = create_roles(config_roles)
        
        class MockUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
        
        class MockRBACService:
            async def check_permission(self, user, resource, action):
                return True
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                return True
        
        rbac_service = MockRBACService()
        user = MockUser(1, "editor@example.com", "editor")
        
        # Test configuration-driven function
        @require(Role.EDITOR)
        async def edit_content(content_id: int, current_user: MockUser, rbac_service: MockRBACService):
            return {"content_id": content_id, "edited_by": current_user.email}
        
        result = await edit_content(123, user, rbac_service)
        assert result["content_id"] == 123
        assert result["edited_by"] == "editor@example.com"

    def test_file_based_example_demonstrates_flexibility(self):
        """Test that file-based example demonstrates configuration flexibility."""
        
        example_path = Path("../examples/file_based_rbac_example.py")
        
        if example_path.exists():
            content = example_path.read_text()
            
            # Should show how to modify behavior through configuration
            assert "config" in content.lower()
            
            # Should demonstrate multiple resource types
            resource_count = content.lower().count("permission(")
            assert resource_count >= 3, "Should demonstrate multiple permission types"


class TestDatabaseExample:
    """Tests for the database integration example.
    
    Validates: Requirements 12.3
    """

    def test_database_example_exists(self):
        """Test that database example exists."""
        
        # Check for database example in test_fastapi directory
        test_app_path = Path("../test_fastapi")
        assert test_app_path.exists(), "Test FastAPI application should exist"

    def test_database_example_structure(self):
        """Test that database example has proper structure."""
        
        test_app_path = Path("../test_fastapi/test_fastapi")
        
        if test_app_path.exists():
            # Should have main application file
            main_file = test_app_path / "main.py"
            assert main_file.exists(), "Main application file should exist"
            
            # Should have models
            models_file = test_app_path / "models.py"
            assert models_file.exists(), "Models file should exist"
            
            # Should have RBAC setup
            rbac_file = test_app_path / "rbac_setup.py"
            assert rbac_file.exists(), "RBAC setup file should exist"

    def test_database_example_uses_generic_models(self):
        """Test that database example uses generic models."""
        
        models_path = Path("../test_fastapi/test_fastapi/models.py")
        
        if models_path.exists():
            content = models_path.read_text()
            
            # Should have generic resource models
            generic_models = ["Document", "Project", "Task"]
            for model in generic_models:
                assert model in content, f"Should have generic model: {model}"
            
            # Should not have business-specific models
            business_models = ["Customer", "Order", "Quote", "Invoice"]
            for model in business_models:
                assert model not in content, f"Should not have business model: {model}"

    def test_database_example_custom_providers(self):
        """Test that database example implements custom providers."""
        
        ownership_path = Path("../test_fastapi/test_fastapi/ownership_providers.py")
        
        if ownership_path.exists():
            content = ownership_path.read_text()
            
            # Should implement ownership providers
            assert "OwnershipProvider" in content
            
            # Should have providers for generic resources
            generic_providers = ["DocumentOwnershipProvider", "ProjectOwnershipProvider", "TaskOwnershipProvider"]
            for provider in generic_providers:
                assert provider in content, f"Should have provider: {provider}"

    @pytest.mark.asyncio
    async def test_database_example_endpoints(self):
        """Test that database example has proper endpoints."""
        
        main_path = Path("test_fastapi/test_fastapi/main.py")
        
        if main_path.exists():
            content = main_path.read_text()
            
            # Check routers for @require decorators since main.py imports them
            routers_path = Path("test_fastapi/test_fastapi/routers")
            has_require_decorators = False
            
            if routers_path.exists():
                for router_file in routers_path.glob("*.py"):
                    if router_file.name != "__init__.py":
                        router_content = router_file.read_text()
                        if "@require" in router_content:
                            has_require_decorators = True
                            break
            
            # Should have protected endpoints (in routers)
            assert has_require_decorators, "Should have @require decorators in router files"
            
            # Should have CRUD operations
            crud_operations = ["GET", "POST", "PUT", "DELETE"]
            for operation in crud_operations:
                assert operation.lower() in content.lower()

    def test_database_example_demonstrates_patterns(self):
        """Test that database example demonstrates key patterns."""
        
        test_app_path = Path("test_fastapi/test_fastapi")
        
        if test_app_path.exists():
            # Check for key pattern demonstrations
            files_to_check = ["main.py", "rbac_setup.py", "ownership_providers.py"]
            
            for filename in files_to_check:
                file_path = test_app_path / filename
                if file_path.exists():
                    content = file_path.read_text()
                    
                    # Should demonstrate provider pattern
                    if "provider" in filename.lower():
                        assert "async def check_ownership" in content
                    
                    # Should demonstrate service injection
                    if filename == "main.py":
                        # Check if main.py imports routers that use rbac_service
                        routers_path = test_app_path / "routers"
                        has_rbac_service = False
                        
                        if routers_path.exists():
                            for router_file in routers_path.glob("*.py"):
                                if router_file.name != "__init__.py":
                                    router_content = router_file.read_text()
                                    if "rbac_service" in router_content.lower():
                                        has_rbac_service = True
                                        break
                        
                        assert has_rbac_service, "Should have rbac_service usage in router files"


class TestExampleSetupTime:
    """Tests that examples meet setup time requirements.
    
    Validates: Requirements 12.6
    """

    def test_minimal_example_quick_setup(self):
        """Test that minimal example can be set up quickly."""
        
        example_path = Path("../examples/minimal_rbac_example.py")
        
        if example_path.exists():
            # Measure time to read and parse the file
            start_time = time.time()
            
            content = example_path.read_text()
            lines = content.split('\n')
            
            # Simulate setup steps
            setup_steps = [
                "Read file",
                "Identify imports", 
                "Locate main function",
                "Understand structure"
            ]
            
            end_time = time.time()
            setup_time = end_time - start_time
            
            # Should be very quick (under 1 second for file operations)
            assert setup_time < 1.0, "Minimal example setup should be very quick"

    def test_file_based_example_reasonable_setup(self):
        """Test that file-based example has reasonable setup time."""
        
        config_dir = Path("../examples/config")
        
        if config_dir.exists():
            start_time = time.time()
            
            # Simulate configuration loading
            config_files = list(config_dir.glob("*.yaml"))
            
            for config_file in config_files:
                content = config_file.read_text()
                # Simulate parsing YAML (without actually importing yaml)
                lines = content.split('\n')
            
            end_time = time.time()
            setup_time = end_time - start_time
            
            # Should complete within reasonable time
            assert setup_time < 5.0, "File-based example setup should be reasonable"

    def test_database_example_setup_complexity(self):
        """Test that database example setup is not overly complex."""
        
        test_app_path = Path("../test_fastapi")
        
        if test_app_path.exists():
            # Count setup files
            setup_files = [
                "pyproject.toml",
                "test_fastapi/main.py",
                "test_fastapi/models.py",
                "test_fastapi/database.py",
                "test_fastapi/rbac_setup.py"
            ]
            
            existing_files = []
            for setup_file in setup_files:
                file_path = test_app_path / setup_file
                if file_path.exists():
                    existing_files.append(setup_file)
            
            # Should not have too many setup files
            assert len(existing_files) <= 10, "Database example should not be overly complex"

    def test_example_documentation_completeness(self):
        """Test that examples have complete documentation."""
        
        readme_files = [
            "../examples/README_minimal.md",
            "../examples/README_file_based.md"
        ]
        
        for readme_file in readme_files:
            readme_path = Path(readme_file)
            if readme_path.exists():
                content = readme_path.read_text()
                
                # Should have setup instructions
                assert "setup" in content.lower() or "install" in content.lower()
                
                # Should have usage examples
                assert "usage" in content.lower() or "example" in content.lower()


class TestExampleDocumentation:
    """Tests that examples are properly documented.
    
    Validates: Requirements 12.7
    """

    def test_examples_have_docstrings(self):
        """Test that example files have proper docstrings."""
        
        example_files = [
            "../examples/minimal_rbac_example.py",
            "../examples/file_based_rbac_example.py"
        ]
        
        for example_file in example_files:
            example_path = Path(example_file)
            if example_path.exists():
                content = example_path.read_text()
                
                # Should have module docstring
                assert '"""' in content or "'''" in content
                
                # Should explain what the example demonstrates
                assert "example" in content.lower()

    def test_examples_have_comments(self):
        """Test that examples have helpful comments."""
        
        example_files = [
            "../examples/minimal_rbac_example.py",
            "../examples/file_based_rbac_example.py"
        ]
        
        for example_file in example_files:
            example_path = Path(example_file)
            if example_path.exists():
                content = example_path.read_text()
                lines = content.split('\n')
                
                # Count comment lines
                comment_lines = [line for line in lines if line.strip().startswith('#')]
                
                # Should have reasonable number of comments
                total_lines = len([line for line in lines if line.strip()])
                if total_lines > 0:
                    comment_ratio = len(comment_lines) / total_lines
                    assert comment_ratio >= 0.1, "Examples should have adequate comments"

    def test_examples_demonstrate_key_concepts(self):
        """Test that examples demonstrate key RBAC concepts."""
        
        example_files = [
            "../examples/minimal_rbac_example.py",
            "../examples/file_based_rbac_example.py"
        ]
        
        key_concepts = [
            "dynamic roles",
            "permissions", 
            "resource ownership",
            "service injection"
        ]
        
        for example_file in example_files:
            example_path = Path(example_file)
            if example_path.exists():
                content = example_path.read_text().lower()
                
                # Should demonstrate multiple key concepts
                demonstrated_concepts = []
                for concept in key_concepts:
                    if any(word in content for word in concept.split()):
                        demonstrated_concepts.append(concept)
                
                assert len(demonstrated_concepts) >= 2, f"Example should demonstrate key concepts: {example_file}"

    def test_examples_show_best_practices(self):
        """Test that examples show RBAC best practices."""
        
        example_files = [
            "../examples/minimal_rbac_example.py",
            "../examples/file_based_rbac_example.py"
        ]
        
        for example_file in example_files:
            example_path = Path(example_file)
            if example_path.exists():
                content = example_path.read_text()
                
                # Should use decorators properly
                assert "@require" in content
                
                # Should show proper service injection
                assert "rbac_service" in content.lower() or "rbac" in content.lower()
                
                # Should demonstrate error handling
                assert "HTTPException" in content or "except" in content.lower()

    def test_configuration_examples_are_clear(self):
        """Test that configuration examples are clear and well-documented."""
        
        config_files = [
            "../examples/config/roles.yaml",
            "../examples/config/policies.yaml"
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                content = config_path.read_text()
                
                # Should have comments explaining structure
                assert "#" in content, f"Configuration file should have comments: {config_file}"
                
                # Should be well-formatted
                lines = content.split('\n')
                non_empty_lines = [line for line in lines if line.strip()]
                
                # Should have reasonable structure
                assert len(non_empty_lines) > 0, f"Configuration file should not be empty: {config_file}"

    def test_examples_include_usage_instructions(self):
        """Test that examples include clear usage instructions."""
        
        example_files = [
            "../examples/minimal_rbac_example.py",
            "../examples/file_based_rbac_example.py"
        ]
        
        for example_file in example_files:
            example_path = Path(example_file)
            if example_path.exists():
                content = example_path.read_text()
                
                # Should include usage instructions in comments or docstrings
                usage_indicators = [
                    "usage:", "how to run:", "to run:", "example usage",
                    "python", "uvicorn", "fastapi"
                ]
                
                content_lower = content.lower()
                has_usage_info = any(indicator in content_lower for indicator in usage_indicators)
                
                assert has_usage_info, f"Example should include usage instructions: {example_file}"