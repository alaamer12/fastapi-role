"""Tests for query filter helpers.

Tests the generic query helper utilities for RBAC-based filtering.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_role.helpers import check_bulk_ownership, get_accessible_resource_ids
from tests.conftest import TestUser as User


class TestQueryHelpers:
    """Test query filter helper functions."""

    @pytest.fixture
    def rbac_service(self):
        """Create mock RBACService."""
        service = MagicMock()
        service.check_resource_ownership = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_accessible_resource_ids_all_allowed(self, rbac_service):
        """Test filtering when all resources are accessible."""
        rbac_service.check_resource_ownership.return_value = True
        user = User(id=1, role="admin")
        candidate_ids = [1, 2, 3, 4, 5]

        result = await get_accessible_resource_ids(
            user, "order", rbac_service, candidate_ids
        )

        assert result == [1, 2, 3, 4, 5]
        assert rbac_service.check_resource_ownership.call_count == 5

    @pytest.mark.asyncio
    async def test_get_accessible_resource_ids_partial_access(self, rbac_service):
        """Test filtering with partial access."""
        # Allow only even IDs
        rbac_service.check_resource_ownership.side_effect = lambda u, rt, rid: rid % 2 == 0
        
        user = User(id=1, role="customer")
        candidate_ids = [1, 2, 3, 4, 5, 6]

        result = await get_accessible_resource_ids(
            user, "order", rbac_service, candidate_ids
        )

        assert result == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_get_accessible_resource_ids_none_allowed(self, rbac_service):
        """Test filtering when no resources are accessible."""
        rbac_service.check_resource_ownership.return_value = False
        user = User(id=1, role="customer")
        candidate_ids = [1, 2, 3]

        result = await get_accessible_resource_ids(
            user, "order", rbac_service, candidate_ids
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_accessible_resource_ids_empty_list(self, rbac_service):
        """Test filtering with empty candidate list."""
        user = User(id=1, role="customer")
        candidate_ids = []

        result = await get_accessible_resource_ids(
            user, "order", rbac_service, candidate_ids
        )

        assert result == []
        rbac_service.check_resource_ownership.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_bulk_ownership_all_allowed(self, rbac_service):
        """Test bulk ownership check when all are allowed."""
        rbac_service.check_resource_ownership.return_value = True
        user = User(id=1, role="admin")
        resource_ids = [1, 2, 3]

        result = await check_bulk_ownership(user, "order", rbac_service, resource_ids)

        assert result == {1: True, 2: True, 3: True}

    @pytest.mark.asyncio
    async def test_check_bulk_ownership_mixed_access(self, rbac_service):
        """Test bulk ownership check with mixed access."""
        # Allow only ID 2
        rbac_service.check_resource_ownership.side_effect = lambda u, rt, rid: rid == 2
        
        user = User(id=1, role="customer")
        resource_ids = [1, 2, 3]

        result = await check_bulk_ownership(user, "order", rbac_service, resource_ids)

        assert result == {1: False, 2: True, 3: False}

    @pytest.mark.asyncio
    async def test_check_bulk_ownership_empty_list(self, rbac_service):
        """Test bulk ownership check with empty list."""
        user = User(id=1, role="customer")
        resource_ids = []

        result = await check_bulk_ownership(user, "order", rbac_service, resource_ids)

        assert result == {}
        rbac_service.check_resource_ownership.assert_not_called()

    @pytest.mark.asyncio
    async def test_helpers_with_different_resource_types(self, rbac_service):
        """Test helpers work with different resource types."""
        rbac_service.check_resource_ownership.return_value = True
        user = User(id=1, role="admin")

        # Test with different resource types
        for resource_type in ["order", "project", "customer", "invoice"]:
            result = await get_accessible_resource_ids(
                user, resource_type, rbac_service, [1, 2]
            )
            assert result == [1, 2]
