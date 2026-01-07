"""Tests for flexible configuration system.

This module tests the enhanced CasbinConfig that supports:
- Custom model content
- Custom model definitions
- Custom filenames
- Custom base directories
"""

import pytest
from pathlib import Path
from fastapi_role.core.config import CasbinConfig


class TestCasbinConfigFlexibility:
    """Test flexible configuration options."""

    def test_custom_model_content(self):
        """Test custom model content string."""
        custom_model = """[request_definition]
r = sub, obj, act, dom

[policy_definition]
p = sub, obj, act, dom, eft

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.obj == p.obj && r.act == p.act && r.dom == p.dom
"""
        config = CasbinConfig(model_content=custom_model)
        
        # Verify model was set up correctly
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None

    def test_custom_model_definitions(self):
        """Test custom model definitions dictionary."""
        custom_definitions = {
            "r": {"r": "sub, obj, act, dom"},
            "p": {"p": "sub, obj, act, dom, eft"},
            "g": {"g": "_, _, _"},
            "e": {"e": "some(where (p.eft == allow))"},
            "m": {"m": "g(r.sub, p.sub, r.dom) && r.obj == p.obj && r.act == p.act"}
        }
        config = CasbinConfig(model_definitions=custom_definitions)
        
        # Verify model was set up correctly
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None

    def test_custom_filenames(self):
        """Test custom model and policy filenames."""
        config = CasbinConfig(
            model_filename="custom_model.conf",
            policy_filename="custom_policy.csv"
        )
        
        model_path = config.get_model_path()
        policy_path = config.get_policy_path()
        
        assert model_path.name == "custom_model.conf"
        assert policy_path.name == "custom_policy.csv"

    def test_custom_base_directory(self):
        """Test custom base directory for platformdirs."""
        config = CasbinConfig(
            app_name="test-app",
            base_directory="my-custom-rbac"
        )
        
        # The filepath should use the custom base directory
        assert "my-custom-rbac" in str(config.filepath)

    def test_custom_filepath_overrides_base_directory(self):
        """Test that custom filepath overrides base directory."""
        custom_path = Path("/tmp/custom/rbac")
        config = CasbinConfig(
            base_directory="should-be-ignored",
            filepath=custom_path
        )
        
        assert config.filepath == custom_path

    def test_all_custom_options_together(self):
        """Test using all custom options together."""
        custom_definitions = {
            "r": {"r": "sub, obj, act"},
            "p": {"p": "sub, obj, act"},
            "e": {"e": "some(where (p.eft == allow))"},
            "m": {"m": "r.sub == p.sub && r.obj == p.obj && r.act == p.act"}
        }
        
        config = CasbinConfig(
            app_name="test-app",
            base_directory="test-rbac",
            model_filename="test_model.conf",
            policy_filename="test_policy.csv",
            superadmin_role="super_admin",
            model_definitions=custom_definitions
        )
        
        assert config.app_name == "test-app"
        assert config.base_directory == "test-rbac"
        assert config.model_filename == "test_model.conf"
        assert config.policy_filename == "test_policy.csv"
        assert config.superadmin_role == "super_admin"
        
        # Verify paths use custom filenames
        assert config.get_model_path().name == "test_model.conf"
        assert config.get_policy_path().name == "test_policy.csv"
        
        # Verify model works
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None

    def test_backward_compatibility(self):
        """Test that old usage patterns still work."""
        # This should work exactly like before
        config = CasbinConfig(app_name="legacy-app")
        
        assert config.app_name == "legacy-app"
        assert config.model_filename == "rbac_model.conf"
        assert config.policy_filename == "rbac_policy.csv"
        
        # Should still create working enforcer
        enforcer = config.get_casbin_enforcer()
        assert enforcer is not None

    def test_model_content_parsing(self):
        """Test that model content is parsed correctly."""
        model_content = """[request_definition]
r = sub, obj, act

[policy_definition]  
p = sub, obj, act, eft

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""
        config = CasbinConfig(model_content=model_content)
        
        # Test that we can add policies and they work
        config.add_policy("admin", "users", "read", "allow")
        config.add_policy("admin", "users", "write", "allow")
        
        enforcer = config.get_casbin_enforcer()
        
        # Test basic enforcement
        assert enforcer.enforce("admin", "users", "read")
        assert enforcer.enforce("admin", "users", "write")
        assert not enforcer.enforce("user", "users", "write")