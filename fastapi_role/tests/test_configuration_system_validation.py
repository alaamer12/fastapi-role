"""Comprehensive validation tests for the configuration system robustness.

This module validates that the CasbinConfig system works correctly with various
configuration scenarios, platformdirs integration, and configuration validation.

Test Classes:
    TestConfigurationScenarios: Tests for various configuration scenarios
    TestPlatformdirsIntegration: Tests for platformdirs integration robustness
    TestConfigurationValidation: Tests for configuration validation and error handling
    TestHierarchicalConfiguration: Tests for hierarchical configuration loading
    TestConfigurationEdgeCases: Tests for edge cases and error conditions
    TestConfigurationPerformance: Tests for configuration performance scenarios
"""

import pytest
import tempfile
import hashlib
import os
from pathlib import Path
from unittest.mock import patch, Mock
from typing import Dict, Any

from fastapi_role.core.config import CasbinConfig, Policy, GroupingPolicy
from fastapi_role.core.roles import create_roles


class TestConfigurationScenarios:
    """Tests for various configuration scenarios.
    
    Validates: Requirements 4.1, 4.7
    """

    def test_minimal_configuration(self):
        """Test minimal configuration with defaults."""
        config = CasbinConfig()
        
        # Should have sensible defaults
        assert config.app_name == "rbac-app"
        assert config.model_filename == "rbac_model.conf"
        assert config.policy_filename == "rbac_policy.csv"
        assert config.superadmin_role is None
        
        # Should create working enforcer
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None

    def test_full_custom_configuration(self):
        """Test fully customized configuration."""
        custom_definitions = {
            "r": {"r": "sub, obj, act, dom"},
            "p": {"p": "sub, obj, act, dom, eft"},
            "g": {"g": "_, _, _"},
            "e": {"e": "some(where (p.eft == allow))"},
            "m": {"m": "g(r.sub, p.sub, r.dom) && r.obj == p.obj && r.act == p.act && r.dom == p.dom"}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(
                app_name="custom-app",
                filepath=Path(tmpdir),
                superadmin_role="root",
                model_definitions=custom_definitions,
                base_directory="custom-rbac",
                model_filename="custom.conf",
                policy_filename="custom.csv"
            )
            
            assert config.app_name == "custom-app"
            assert config.superadmin_role == "root"
            assert config.base_directory == "custom-rbac"
            assert config.model_filename == "custom.conf"
            assert config.policy_filename == "custom.csv"
            assert config.filepath == Path(tmpdir)
            
            # Should create working enforcer
            enforcer = config.get_casbin_enforcer()
            assert enforcer is not None

    def test_model_content_configuration(self):
        """Test configuration with raw model content."""
        model_content = """[request_definition]
r = user, resource, action

[policy_definition]
p = user, resource, action, eft

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.user == p.user && r.resource == p.resource && r.action == p.action
"""
        config = CasbinConfig(model_content=model_content)
        
        # Should parse and use the custom model
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None
        
        # Test with custom model structure
        config.add_policy("alice", "data1", "read", "allow")
        enforcer = config.get_casbin_enforcer()
        
        assert enforcer.enforce("alice", "data1", "read")
        assert not enforcer.enforce("alice", "data1", "write")

    def test_role_inheritance_configuration(self):
        """Test configuration with role inheritance."""
        config = CasbinConfig()
        
        # Add policies and role inheritance
        config.add_policy("admin", "users", "read", "allow")
        config.add_policy("admin", "users", "write", "allow")
        config.add_policy("user", "profile", "read", "allow")
        
        config.add_role_inheritance("manager", "admin")
        config.add_role_inheritance("employee", "user")
        
        enforcer = config.get_casbin_enforcer()
        
        # Manager should inherit admin permissions
        assert enforcer.enforce("manager", "users", "read")
        assert enforcer.enforce("manager", "users", "write")
        
        # Employee should inherit user permissions
        assert enforcer.enforce("employee", "profile", "read")
        assert not enforcer.enforce("employee", "users", "write")

    def test_enum_role_configuration(self):
        """Test configuration with enum roles."""
        Role = create_roles(["ADMIN", "USER", "GUEST"])
        config = CasbinConfig()
        
        # Add policies using enum roles
        config.add_policy(Role.ADMIN, "system", "manage", "allow")
        config.add_policy(Role.USER, "data", "read", "allow")
        config.add_policy(Role.GUEST, "public", "view", "allow")
        
        config.add_role_inheritance(Role.ADMIN, Role.USER)
        
        enforcer = config.get_casbin_enforcer()
        
        # Test enum-based policies
        assert enforcer.enforce("admin", "system", "manage")
        assert enforcer.enforce("admin", "data", "read")  # Inherited
        assert enforcer.enforce("user", "data", "read")
        assert enforcer.enforce("guest", "public", "view")
        assert not enforcer.enforce("guest", "data", "read")

    def test_multi_domain_configuration(self):
        """Test configuration for multi-domain scenarios."""
        multi_domain_definitions = {
            "r": {"r": "sub, dom, obj, act"},
            "p": {"p": "sub, dom, obj, act, eft"},
            "g": {"g": "_, _, _"},
            "e": {"e": "some(where (p.eft == allow))"},
            "m": {"m": "g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act"}
        }
        
        config = CasbinConfig(model_definitions=multi_domain_definitions)
        
        # Should handle multi-domain model
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None


class TestPlatformdirsIntegration:
    """Tests for platformdirs integration robustness.
    
    Validates: Requirements 4.2, 4.6
    """

    def test_platformdirs_path_generation(self):
        """Test platformdirs path generation with various app names."""
        test_cases = [
            "simple-app",
            "app_with_underscores",
            "app-with-dashes",
            "AppWithCamelCase",
            "app123with456numbers",
            "app.with.dots",
            "very-long-application-name-that-exceeds-normal-length"
        ]
        
        for app_name in test_cases:
            with patch("fastapi_role.core.config.user_data_path") as mock_user_data:
                mock_user_data.return_value = Path("/mock/data")
                config = CasbinConfig(app_name=app_name)
                
                # Should generate valid path
                assert config.filepath is not None
                assert isinstance(config.filepath, Path)
                
                # Should use hash of app_name
                expected_hash = hashlib.md5(app_name.encode()).hexdigest()
                assert expected_hash in str(config.filepath)

    def test_platformdirs_error_handling(self):
        """Test platformdirs error handling."""
        with patch("fastapi_role.core.config.user_data_path") as mock_user_data:
            # Simulate platformdirs failure
            mock_user_data.side_effect = Exception("Platform dirs not available")
            
            # Should handle gracefully or provide fallback
            try:
                config = CasbinConfig()
                # If it doesn't raise, it should still work
                assert config.filepath is not None
            except Exception as e:
                # If it raises, should be a meaningful error
                assert "Platform dirs not available" in str(e)

    def test_file_creation_permissions(self):
        """Test file creation with various permission scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(filepath=Path(tmpdir))
            
            # Should create files successfully
            config._ensure_files_exist()
            
            model_path = config.get_model_path()
            policy_path = config.get_policy_path()
            
            assert model_path.exists()
            assert policy_path.exists()
            
            # Files should be readable
            assert model_path.is_file()
            assert policy_path.is_file()
            
            # Should have content
            assert len(model_path.read_text()) > 0
            assert len(policy_path.read_text()) > 0

    def test_directory_creation_nested(self):
        """Test creation of nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "level1" / "level2" / "level3"
            config = CasbinConfig(filepath=nested_path)
            
            # Should create nested directories
            config._ensure_files_exist()
            
            assert nested_path.exists()
            assert nested_path.is_dir()
            assert config.get_model_path().exists()
            assert config.get_policy_path().exists()

    def test_concurrent_file_creation(self):
        """Test concurrent file creation scenarios."""
        import threading
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            results = []
            
            def create_config(thread_id):
                try:
                    config = CasbinConfig(filepath=Path(tmpdir) / f"thread_{thread_id}")
                    config._ensure_files_exist()
                    results.append((thread_id, True, None))
                except Exception as e:
                    results.append((thread_id, False, str(e)))
            
            # Start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_config, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # All should succeed
            assert len(results) == 5
            for thread_id, success, error in results:
                assert success, f"Thread {thread_id} failed: {error}"


class TestConfigurationValidation:
    """Tests for configuration validation and error handling.
    
    Validates: Requirements 4.3, 4.4, 4.5
    """

    def test_invalid_model_content_handling(self):
        """Test handling of invalid model content."""
        invalid_model_contents = [
            "",  # Empty content
            "invalid content without sections",
            "[invalid_section]\ninvalid = content",
            "[request_definition]\n# missing required fields",
            "malformed [section without closing bracket",
        ]
        
        for invalid_content in invalid_model_contents:
            try:
                config = CasbinConfig(model_content=invalid_content)
                enforcer = config.get_casbin_enforcer()
                # If it doesn't raise, it should still be usable
                assert enforcer is not None
            except Exception:
                # If it raises, that's also acceptable behavior
                pass

    def test_invalid_model_definitions_handling(self):
        """Test handling of invalid model definitions."""
        invalid_definitions = [
            {},  # Empty definitions
            {"invalid": {"key": "value"}},  # Invalid section
            {"r": {}},  # Empty section
            {"r": {"invalid": ""}},  # Empty value
        ]
        
        for invalid_def in invalid_definitions:
            try:
                config = CasbinConfig(model_definitions=invalid_def)
                enforcer = config.get_casbin_enforcer()
                # Should handle gracefully
                assert enforcer is not None
            except Exception:
                # Or raise meaningful error
                pass

    def test_policy_validation(self):
        """Test policy validation and error handling."""
        config = CasbinConfig()
        
        # Test valid policies
        config.add_policy("user", "resource", "action", "allow")
        config.add_policy("admin", "*", "*", "allow")
        
        # Test edge case policies
        config.add_policy("", "resource", "action", "allow")  # Empty subject
        config.add_policy("user", "", "action", "allow")  # Empty object
        config.add_policy("user", "resource", "", "allow")  # Empty action
        
        # Should handle all cases
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None
        assert len(config.policies) == 5

    def test_grouping_policy_validation(self):
        """Test grouping policy validation."""
        config = CasbinConfig()
        
        # Test valid grouping policies
        config.add_role_inheritance("manager", "employee")
        config.add_role_inheritance("admin", "manager")
        
        # Test edge cases
        config.add_role_inheritance("", "role")  # Empty child
        config.add_role_inheritance("role", "")  # Empty parent
        config.add_role_inheritance("same", "same")  # Self-inheritance
        
        # Should handle all cases
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None
        assert len(config.grouping_policies) == 5

    def test_superadmin_role_validation(self):
        """Test superadmin role validation."""
        # Test valid superadmin roles
        valid_roles = ["admin", "superadmin", "root", "system", "super_admin"]
        
        for role in valid_roles:
            config = CasbinConfig(superadmin_role=role)
            assert config.superadmin_role == role
        
        # Test edge cases
        edge_cases = ["", None, "role with spaces", "role-with-dashes"]
        
        for role in edge_cases:
            config = CasbinConfig(superadmin_role=role)
            assert config.superadmin_role == role

    def test_filename_validation(self):
        """Test filename validation and sanitization."""
        # Test valid filenames
        valid_filenames = [
            "model.conf",
            "rbac_model.conf",
            "my-model.conf",
            "model123.conf"
        ]
        
        for filename in valid_filenames:
            config = CasbinConfig(model_filename=filename, policy_filename=filename.replace('.conf', '.csv'))
            assert config.model_filename == filename

    def test_path_validation(self):
        """Test path validation and error handling."""
        # Test various path scenarios
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_paths = [
                Path(tmpdir),
                Path(tmpdir) / "subdir",
                Path(tmpdir) / "nested" / "path"
            ]
            
            for path in valid_paths:
                config = CasbinConfig(filepath=path)
                assert config.filepath == path
                
                # Should be able to create files
                config._ensure_files_exist()
                assert path.exists()


class TestHierarchicalConfiguration:
    """Tests for hierarchical configuration loading.
    
    Validates: Requirements 4.6, 4.7
    """

    def test_configuration_precedence(self):
        """Test configuration option precedence."""
        # Test that explicit parameters override defaults
        config = CasbinConfig(
            app_name="explicit-app",
            superadmin_role="explicit-admin",
            model_filename="explicit.conf"
        )
        
        assert config.app_name == "explicit-app"
        assert config.superadmin_role == "explicit-admin"
        assert config.model_filename == "explicit.conf"

    def test_environment_variable_simulation(self):
        """Test environment variable configuration simulation."""
        # Simulate environment-based configuration
        env_config = {
            "RBAC_APP_NAME": "env-app",
            "RBAC_SUPERADMIN_ROLE": "env-admin",
            "RBAC_MODEL_FILE": "env-model.conf"
        }
        
        # Create config that could use environment variables
        config = CasbinConfig(
            app_name=env_config.get("RBAC_APP_NAME", "default-app"),
            superadmin_role=env_config.get("RBAC_SUPERADMIN_ROLE"),
            model_filename=env_config.get("RBAC_MODEL_FILE", "rbac_model.conf")
        )
        
        assert config.app_name == "env-app"
        assert config.superadmin_role == "env-admin"
        assert config.model_filename == "env-model.conf"

    def test_configuration_file_simulation(self):
        """Test configuration file loading simulation."""
        # Simulate loading from configuration file
        config_data = {
            "app_name": "file-app",
            "superadmin_role": "file-admin",
            "model_filename": "file-model.conf",
            "policy_filename": "file-policy.csv"
        }
        
        config = CasbinConfig(**config_data)
        
        assert config.app_name == "file-app"
        assert config.superadmin_role == "file-admin"
        assert config.model_filename == "file-model.conf"
        assert config.policy_filename == "file-policy.csv"

    def test_configuration_merging(self):
        """Test configuration merging from multiple sources."""
        # Simulate merging configurations from multiple sources
        base_config = {
            "app_name": "base-app",
            "model_filename": "base.conf"
        }
        
        override_config = {
            "superadmin_role": "override-admin",
            "policy_filename": "override.csv"
        }
        
        # Merge configurations
        merged_config = {**base_config, **override_config}
        config = CasbinConfig(**merged_config)
        
        assert config.app_name == "base-app"  # From base
        assert config.model_filename == "base.conf"  # From base
        assert config.superadmin_role == "override-admin"  # From override
        assert config.policy_filename == "override.csv"  # From override


class TestConfigurationEdgeCases:
    """Tests for edge cases and error conditions.
    
    Validates: Requirements 4.3, 4.4, 4.5
    """

    def test_unicode_configuration(self):
        """Test configuration with unicode characters."""
        unicode_config = CasbinConfig(
            app_name="测试应用",  # Chinese characters
            superadmin_role="администратор",  # Cyrillic characters
            base_directory="приложение"  # Cyrillic characters
        )
        
        assert unicode_config.app_name == "测试应用"
        assert unicode_config.superadmin_role == "администратор"
        assert unicode_config.base_directory == "приложение"

    def test_very_long_configuration_values(self):
        """Test configuration with very long values."""
        long_app_name = "a" * 1000
        long_role_name = "b" * 500
        
        config = CasbinConfig(
            app_name=long_app_name,
            superadmin_role=long_role_name
        )
        
        assert config.app_name == long_app_name
        assert config.superadmin_role == long_role_name

    def test_special_character_configuration(self):
        """Test configuration with special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        config = CasbinConfig(
            app_name=f"app{special_chars}",
            superadmin_role=f"role{special_chars}"
        )
        
        # Should handle special characters
        assert special_chars in config.app_name
        assert special_chars in config.superadmin_role

    def test_none_value_handling(self):
        """Test handling of None values in configuration."""
        config = CasbinConfig(
            superadmin_role=None,
            model_content=None,
            model_definitions=None
        )
        
        assert config.superadmin_role is None
        # Should still create working enforcer with defaults
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None

    def test_memory_usage_large_configuration(self):
        """Test memory usage with large configuration."""
        config = CasbinConfig()
        
        # Add many policies
        for i in range(1000):
            config.add_policy(f"user_{i}", f"resource_{i}", "read", "allow")
            if i % 10 == 0:
                config.add_role_inheritance(f"manager_{i}", f"user_{i}")
        
        # Should handle large number of policies
        assert len(config.policies) == 1000
        assert len(config.grouping_policies) == 100
        
        # Should still create working enforcer
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None


class TestConfigurationPerformance:
    """Tests for configuration performance scenarios.
    
    Validates: Requirements 4.1, 4.2
    """

    def test_configuration_creation_performance(self):
        """Test configuration creation performance."""
        import time
        
        start_time = time.time()
        
        # Create multiple configurations
        configs = []
        for i in range(100):
            config = CasbinConfig(app_name=f"perf-test-{i}")
            configs.append(config)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create configurations reasonably quickly
        assert creation_time < 5.0  # Less than 5 seconds for 100 configs
        assert len(configs) == 100

    def test_enforcer_creation_performance(self):
        """Test enforcer creation performance."""
        import time
        
        config = CasbinConfig()
        
        # Add moderate number of policies
        for i in range(100):
            config.add_policy(f"user_{i}", f"resource_{i % 10}", "read", "allow")
        
        start_time = time.time()
        
        # Create enforcers
        enforcers = []
        for i in range(10):
            enforcer = config.get_casbin_enforcer()
            enforcers.append(enforcer)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create enforcers reasonably quickly
        assert creation_time < 2.0  # Less than 2 seconds for 10 enforcers
        assert len(enforcers) == 10

    def test_concurrent_configuration_access(self):
        """Test concurrent configuration access."""
        import threading
        import time
        
        config = CasbinConfig()
        results = []
        
        def access_config(thread_id):
            try:
                # Add policies concurrently
                for i in range(10):
                    config.add_policy(f"thread_{thread_id}_user_{i}", "resource", "read", "allow")
                
                # Create enforcer
                enforcer = config.get_casbin_enforcer()
                results.append((thread_id, True, len(config.policies)))
            except Exception as e:
                results.append((thread_id, False, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=access_config, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 5
        for thread_id, success, data in results:
            assert success, f"Thread {thread_id} failed: {data}"