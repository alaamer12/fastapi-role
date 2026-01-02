"""Performance tests for generic filtering operations.

This module restores performance tests for filtering and bulk operations,
adapted for the generic library architecture.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_role import RBACService
from tests.conftest import TestRole as Role
from tests.conftest import TestUser as User


class TestGenericFilteringPerformance:
    """Test performance of generic filtering operations."""

    @pytest.fixture
    def rbac_service(self):
        """Create RBAC service with mocked database."""
        mock_db = AsyncMock()
        with patch("casbin.Enforcer"):
            service = RBACService(mock_db)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_in_memory_filtering_performance(self, rbac_service):
        """Test performance of filtering a large list of items."""
        # Setup
        user = User(id=1, role=Role.CUSTOMER.value)
        items = [{"id": i, "owner_id": i % 10} for i in range(1000)]
        
        # Mock ownership check to simulate some logic
        # For example, user owns items where owner_id == 1
        async def mock_check_ownership(user, r_type, r_id):
            # Simulate slight overhead
            return (r_id % 10) == 1

        rbac_service.check_resource_ownership = AsyncMock(side_effect=mock_check_ownership)

        start_time = time.time()
        
        # Filter items
        filtered_items = []
        for item in items:
            if await rbac_service.check_resource_ownership(user, "item", item["id"]):
                filtered_items.append(item)
                
        duration = time.time() - start_time
        
        # Should be fast (1000 items)
        # Even with async overhead, should be well under 1s for 1000 items
        assert duration < 1.0, f"Filtering 1000 items took {duration:.3f}s"
        assert len(filtered_items) == 100

    @pytest.mark.asyncio
    async def test_bulk_permission_check_performance(self, rbac_service):
        """Test performance of bulk permission checks."""
        user = User(id=1, role=Role.CUSTOMER.value)
        resources = [f"resource_{i}" for i in range(1000)]
        
        # Mock permission check
        rbac_service.enforcer.enforce.return_value = True
        
        start_time = time.time()
        
        # Bulk check
        results = []
        for resource in resources:
            # We bypass the service wrapper to test specific parts? 
            # No, we test the service method.
            # But the service method caches, so we test the caching mechanism too?
            # If we reuse same resource keys, cache is hit.
            # If we use unique resources, cache is populated (simulating first load of a list view)
            res = await rbac_service.check_permission(user, resource, "read")
            results.append(res)
            
        duration = time.time() - start_time
        
        assert duration < 2.0, f"Bulk check of 1000 items took {duration:.3f}s"
