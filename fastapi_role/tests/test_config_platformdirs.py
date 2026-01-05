"""Tests for CasbinConfig platformdirs integration.

Tests the dynamic file generation, app_name hashing, and platformdirs usage.
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from fastapi_role.core.config import CasbinConfig


class TestCasbinConfigPlatformdirs:
    """Test CasbinConfig platformdirs integration."""

    def test_default_app_name(self):
        """Test default app_name is 'fastapi-role'."""
        config = CasbinConfig()
        assert config.app_name == "fastapi-role"

    def test_custom_app_name(self):
        """Test custom app_name."""
        config = CasbinConfig(app_name="my-custom-app")
        assert config.app_name == "my-custom-app"

    def test_default_filepath_uses_hash(self):
        """Test default filepath uses MD5 hash of app_name."""
        app_name = "test-app"
        expected_hash = hashlib.md5(app_name.encode()).hexdigest()
        
        with patch("fastapi_role.core.config.user_data_path") as mock_user_data:
            mock_user_data.return_value = Path("/mock/data")
            config = CasbinConfig(app_name=app_name)
            
            assert config.filepath == Path("/mock/data") / "roles" / expected_hash

    def test_custom_filepath_overrides_default(self):
        """Test custom filepath overrides platformdirs default."""
        custom_path = Path("/custom/path")
        config = CasbinConfig(filepath=custom_path)
        assert config.filepath == custom_path

    def test_different_app_names_different_hashes(self):
        """Test different app_names produce different directory hashes."""
        with patch("fastapi_role.core.config.user_data_path") as mock_user_data:
            mock_user_data.return_value = Path("/mock/data")
            
            config1 = CasbinConfig(app_name="app1")
            config2 = CasbinConfig(app_name="app2")
            
            assert config1.filepath != config2.filepath

    def test_get_model_path(self):
        """Test get_model_path returns correct file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(filepath=Path(tmpdir))
            model_path = config.get_model_path()
            
            assert model_path == Path(tmpdir) / "rbac_model.conf"

    def test_get_policy_path(self):
        """Test get_policy_path returns correct file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(filepath=Path(tmpdir))
            policy_path = config.get_policy_path()
            
            assert policy_path == Path(tmpdir) / "rbac_policy.csv"

    def test_ensure_files_exist_creates_directory(self):
        """Test _ensure_files_exist creates directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_subdir"
            config = CasbinConfig(filepath=test_path)
            
            assert not test_path.exists()
            config._ensure_files_exist()
            assert test_path.exists()

    def test_ensure_files_exist_creates_model_file(self):
        """Test _ensure_files_exist creates rbac_model.conf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(filepath=Path(tmpdir))
            model_path = config.get_model_path()
            
            assert not model_path.exists()
            config._ensure_files_exist()
            assert model_path.exists()
            
            # Verify content
            content = model_path.read_text()
            assert "[request_definition]" in content
            assert "[policy_definition]" in content
            assert "[role_definition]" in content

    def test_ensure_files_exist_creates_policy_file(self):
        """Test _ensure_files_exist creates rbac_policy.csv."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(filepath=Path(tmpdir))
            policy_path = config.get_policy_path()
            
            assert not policy_path.exists()
            config._ensure_files_exist()
            assert policy_path.exists()
            
            # Verify content
            content = policy_path.read_text()
            assert "# Default RBAC policies" in content

    def test_ensure_files_exist_idempotent(self):
        """Test _ensure_files_exist is idempotent (doesn't overwrite)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CasbinConfig(filepath=Path(tmpdir))
            
            # First call
            config._ensure_files_exist()
            model_path = config.get_model_path()
            
            # Modify file
            model_path.write_text("CUSTOM CONTENT")
            
            # Second call should not overwrite
            config._ensure_files_exist()
            assert model_path.read_text() == "CUSTOM CONTENT"

    def test_hash_consistency(self):
        """Test same app_name always produces same hash."""
        app_name = "consistent-app"
        
        with patch("fastapi_role.core.config.user_data_path") as mock_user_data:
            mock_user_data.return_value = Path("/mock/data")
            
            config1 = CasbinConfig(app_name=app_name)
            config2 = CasbinConfig(app_name=app_name)
            
            assert config1.filepath == config2.filepath
