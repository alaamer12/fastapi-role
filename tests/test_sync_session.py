"""Tests for synchronous session support in BaseService and RBACService.

This module tests the sync/async session support added to the library,
ensuring both session types work correctly and that runtime validation
prevents misuse.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_role.base import BaseService
from fastapi_role.rbac_service import RBACService
from fastapi_role.core.config import CasbinConfig
from fastapi_role.exception import DatabaseException
from tests.conftest import TestUser, TestRole as Role


class TestBaseServiceSyncSession:
    """Test BaseService with synchronous sessions."""

    @pytest.fixture
    def sync_session(self):
        """Create a mock synchronous session."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def base_service(self, sync_session):
        """Create BaseService with sync session."""
        return BaseService(sync_session)

    def test_init_with_sync_session(self, base_service, sync_session):
        """Test BaseService initialization with sync session."""
        assert base_service.db == sync_session
        assert base_service._is_async is False

    def test_commit_sync_success(self, base_service, sync_session):
        """Test successful sync commit."""
        base_service.commit_sync()
        sync_session.commit.assert_called_once()

    def test_commit_sync_with_rollback(self, base_service, sync_session):
        """Test sync commit with exception triggers rollback."""
        sync_session.commit.side_effect = Exception("Commit failed")
        
        with pytest.raises(DatabaseException) as exc_info:
            base_service.commit_sync()
        
        sync_session.rollback.assert_called_once()
        assert "Failed to commit transaction" in str(exc_info.value)

    def test_rollback_sync(self, base_service, sync_session):
        """Test sync rollback."""
        base_service.rollback_sync()
        sync_session.rollback.assert_called_once()

    def test_refresh_sync(self, base_service, sync_session):
        """Test sync refresh."""
        instance = Mock()
        base_service.refresh_sync(instance)
        sync_session.refresh.assert_called_once_with(instance)

    def test_async_commit_raises_error(self, base_service):
        """Test that async commit raises error with sync session."""
        with pytest.raises(RuntimeError) as exc_info:
            # Can't use await in sync test, but we can call the method
            # and check it raises immediately
            import asyncio
            try:
                asyncio.run(base_service.commit())
            except RuntimeError as e:
                raise e
        
        assert "Cannot use async commit() with synchronous session" in str(exc_info.value)

    def test_async_rollback_raises_error(self, base_service):
        """Test that async rollback raises error with sync session."""
        with pytest.raises(RuntimeError) as exc_info:
            import asyncio
            try:
                asyncio.run(base_service.rollback())
            except RuntimeError as e:
                raise e
        
        assert "Cannot use async rollback() with synchronous session" in str(exc_info.value)

    def test_async_refresh_raises_error(self, base_service):
        """Test that async refresh raises error with sync session."""
        instance = Mock()
        with pytest.raises(RuntimeError) as exc_info:
            import asyncio
            try:
                asyncio.run(base_service.refresh(instance))
            except RuntimeError as e:
                raise e
        
        assert "Cannot use async refresh() with synchronous session" in str(exc_info.value)


class TestBaseServiceAsyncSession:
    """Test BaseService with asynchronous sessions (backward compatibility)."""

    @pytest.fixture
    def async_session(self):
        """Create a mock asynchronous session."""
        session = Mock(spec=AsyncSession)
        # Make commit, rollback, refresh async using AsyncMock
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def base_service(self, async_session):
        """Create BaseService with async session."""
        return BaseService(async_session)

    def test_init_with_async_session(self, base_service, async_session):
        """Test BaseService initialization with async session."""
        assert base_service.db == async_session
        assert base_service._is_async is True

    @pytest.mark.asyncio
    async def test_commit_async_success(self, base_service, async_session):
        """Test successful async commit."""
        await base_service.commit()
        async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_async_with_rollback(self, base_service, async_session):
        """Test async commit with exception triggers rollback."""
        async_session.commit.side_effect = Exception("Commit failed")
        
        with pytest.raises(DatabaseException) as exc_info:
            await base_service.commit()
        
        async_session.rollback.assert_called_once()
        assert "Failed to commit transaction" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_async(self, base_service, async_session):
        """Test async rollback."""
        await base_service.rollback()
        async_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_async(self, base_service, async_session):
        """Test async refresh."""
        instance = Mock()
        await base_service.refresh(instance)
        async_session.refresh.assert_called_once_with(instance)

    def test_sync_commit_raises_error(self, base_service):
        """Test that sync commit raises error with async session."""
        with pytest.raises(RuntimeError) as exc_info:
            base_service.commit_sync()
        
        assert "Cannot use sync commit_sync() with asynchronous session" in str(exc_info.value)

    def test_sync_rollback_raises_error(self, base_service):
        """Test that sync rollback raises error with async session."""
        with pytest.raises(RuntimeError) as exc_info:
            base_service.rollback_sync()
        
        assert "Cannot use sync rollback_sync() with asynchronous session" in str(exc_info.value)

    def test_sync_refresh_raises_error(self, base_service):
        """Test that sync refresh raises error with async session."""
        instance = Mock()
        with pytest.raises(RuntimeError) as exc_info:
            base_service.refresh_sync(instance)
        
        assert "Cannot use sync refresh_sync() with asynchronous session" in str(exc_info.value)


class TestRBACServiceSyncSession:
    """Test RBACService with synchronous sessions."""

    @pytest.fixture
    def sync_session(self):
        """Create a mock synchronous session."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def casbin_config(self):
        """Create a test Casbin configuration."""
        return CasbinConfig(app_name="test_sync")

    @pytest.fixture
    def rbac_service(self, sync_session, casbin_config):
        """Create RBACService with sync session."""
        return RBACService(sync_session, config=casbin_config)

    def test_init_with_sync_session(self, rbac_service, sync_session):
        """Test RBACService initialization with sync session."""
        assert rbac_service.db == sync_session
        assert rbac_service._is_async is False

    def test_assign_role_to_user_sync(self, rbac_service, sync_session):
        """Test sync role assignment."""
        user = TestUser(id=1, email="test@example.com", role="customer")
        
        rbac_service.assign_role_to_user_sync(user, Role.SALESMAN)
        
        assert user.role == "salesman"
        sync_session.commit.assert_called_once()

    def test_assign_role_to_user_sync_clears_cache(self, rbac_service, sync_session):
        """Test that sync role assignment clears cache."""
        user = TestUser(id=1, email="test@example.com", role="customer")
        
        # Populate cache
        rbac_service.cache_provider.set("test_key", True)
        assert rbac_service.cache_provider.get("test_key") is True
        
        rbac_service.assign_role_to_user_sync(user, Role.SALESMAN)
        
        # Cache should be cleared
        assert rbac_service.cache_provider.get("test_key") is None


class TestRBACServiceAsyncSession:
    """Test RBACService with asynchronous sessions (backward compatibility)."""

    @pytest.fixture
    def async_session(self):
        """Create a mock asynchronous session."""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def casbin_config(self):
        """Create a test Casbin configuration."""
        return CasbinConfig(app_name="test_async")

    @pytest.fixture
    def rbac_service(self, async_session, casbin_config):
        """Create RBACService with async session."""
        return RBACService(async_session, config=casbin_config)

    def test_init_with_async_session(self, rbac_service, async_session):
        """Test RBACService initialization with async session."""
        assert rbac_service.db == async_session
        assert rbac_service._is_async is True

    @pytest.mark.asyncio
    async def test_assign_role_to_user_async(self, rbac_service, async_session):
        """Test async role assignment (existing behavior)."""
        user = TestUser(id=1, email="test@example.com", role="customer")
        
        await rbac_service.assign_role_to_user(user, Role.SALESMAN)
        
        assert user.role == "salesman"
        async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_role_to_user_async_clears_cache(self, rbac_service, async_session):
        """Test that async role assignment clears cache."""
        user = TestUser(id=1, email="test@example.com", role="customer")
        
        # Populate cache
        rbac_service.cache_provider.set("test_key", True)
        assert rbac_service.cache_provider.get("test_key") is True
        
        await rbac_service.assign_role_to_user(user, Role.SALESMAN)
        
        # Cache should be cleared
        assert rbac_service.cache_provider.get("test_key") is None
