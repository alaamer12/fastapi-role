"""Tests for provider protocols and default implementations.

Tests the SubjectProvider, RoleProvider, and CacheProvider protocols
along with their default implementations.
"""

import pytest

from fastapi_role.providers import (
    DefaultCacheProvider,
    DefaultRoleProvider,
    DefaultSubjectProvider,
)
from tests.conftest import TestUser as User


class TestDefaultSubjectProvider:
    """Test DefaultSubjectProvider functionality."""

    def test_get_subject_default_email(self):
        """Test default subject provider returns user email."""
        provider = DefaultSubjectProvider()
        user = User(id=1, email="test@example.com", role="customer")

        subject = provider.get_subject(user)
        assert subject == "test@example.com"

    def test_get_subject_custom_field(self):
        """Test subject provider with custom field name."""
        provider = DefaultSubjectProvider(field_name="id")
        user = User(id=123, email="test@example.com", role="customer")

        subject = provider.get_subject(user)
        assert subject == "123"

    def test_get_subject_username_field(self):
        """Test subject provider with username field."""
        provider = DefaultSubjectProvider(field_name="username")
        user = User(id=1, email="test@example.com", role="customer", username="testuser")

        subject = provider.get_subject(user)
        assert subject == "testuser"


class TestDefaultRoleProvider:
    """Test DefaultRoleProvider functionality."""

    def test_get_role(self):
        """Test get_role returns user role."""
        provider = DefaultRoleProvider()
        user = User(id=1, role="customer")

        role = provider.get_role(user)
        assert role == "customer"

    def test_has_role_match(self):
        """Test has_role returns True for matching role."""
        provider = DefaultRoleProvider()
        user = User(id=1, role="admin")

        assert provider.has_role(user, "admin") is True

    def test_has_role_no_match(self):
        """Test has_role returns False for non-matching role."""
        provider = DefaultRoleProvider()
        user = User(id=1, role="customer")

        assert provider.has_role(user, "admin") is False

    def test_has_role_superadmin_bypass(self):
        """Test superadmin role bypasses all role checks."""
        provider = DefaultRoleProvider(superadmin_role="superadmin")
        user = User(id=1, role="superadmin")

        # Superadmin should have all roles
        assert provider.has_role(user, "admin") is True
        assert provider.has_role(user, "customer") is True
        assert provider.has_role(user, "any_role") is True

    def test_has_role_custom_superadmin(self):
        """Test custom superadmin role name."""
        provider = DefaultRoleProvider(superadmin_role="root")
        root_user = User(id=1, role="root")
        admin_user = User(id=2, role="superadmin")

        # Root should bypass
        assert provider.has_role(root_user, "admin") is True
        # Superadmin should not bypass with custom config
        assert provider.has_role(admin_user, "admin") is False


class TestDefaultCacheProvider:
    """Test DefaultCacheProvider functionality."""

    def test_get_miss(self):
        """Test cache miss returns None."""
        provider = DefaultCacheProvider()

        result = provider.get("nonexistent")
        assert result is None

    def test_set_and_get(self):
        """Test setting and getting cached values."""
        provider = DefaultCacheProvider()

        provider.set("key1", True)
        provider.set("key2", False)

        assert provider.get("key1") is True
        assert provider.get("key2") is False

    def test_clear(self):
        """Test clearing cache."""
        provider = DefaultCacheProvider()

        provider.set("key1", True)
        provider.set("key2", False)

        provider.clear()

        assert provider.get("key1") is None
        assert provider.get("key2") is None

    def test_get_stats_empty(self):
        """Test stats for empty cache."""
        provider = DefaultCacheProvider()

        stats = provider.get_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

    def test_get_stats_with_hits_and_misses(self):
        """Test stats tracking hits and misses."""
        provider = DefaultCacheProvider()

        provider.set("key1", True)

        # Hit
        provider.get("key1")
        # Miss
        provider.get("key2")
        # Hit
        provider.get("key1")

        stats = provider.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2 / 3

    def test_ttl_expiration(self):
        """Test TTL expiration removes cached values."""
        import time

        provider = DefaultCacheProvider()

        # Set with 1 second TTL
        provider.set("key1", True, ttl=1)

        # Should be available immediately
        assert provider.get("key1") is True

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert provider.get("key1") is None

    def test_default_ttl(self):
        """Test default TTL is applied."""
        import time

        provider = DefaultCacheProvider(default_ttl=1)

        # Set without explicit TTL (uses default)
        provider.set("key1", True)

        # Should be available immediately
        assert provider.get("key1") is True

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert provider.get("key1") is None

    def test_no_ttl_persists(self):
        """Test values without TTL persist."""
        import time

        provider = DefaultCacheProvider()

        provider.set("key1", True)

        # Wait a bit
        time.sleep(0.5)

        # Should still be available
        assert provider.get("key1") is True

    def test_override_default_ttl(self):
        """Test explicit TTL overrides default TTL."""
        import time

        provider = DefaultCacheProvider(default_ttl=10)

        # Set with explicit short TTL
        provider.set("key1", True, ttl=1)

        # Wait for short TTL to expire
        time.sleep(1.1)

        # Should be expired despite longer default TTL
        assert provider.get("key1") is None
