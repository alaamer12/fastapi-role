"""Query filter helpers for RBAC-based data access control.

This module provides generic utilities for filtering database queries based on
user permissions and resource ownership.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from fastapi_role.protocols import UserProtocol
    from fastapi_role.rbac_service import RBACService


async def get_accessible_resource_ids(
    user: UserProtocol,
    resource_type: str,
    service: RBACService,
    candidate_ids: List[Any],
) -> List[Any]:
    """Get list of resource IDs user can access from candidates.
    
    Filters a list of candidate resource IDs based on ownership checks.
    
    Args:
        user: The user to check access for.
        resource_type: Type of resource being filtered.
        service: RBACService instance for ownership checks.
        candidate_ids: List of resource IDs to filter.
        
    Returns:
        List[Any]: Filtered list of accessible resource IDs.
        
    Example:
        ```python
        # Get all order IDs user can access
        all_order_ids = [1, 2, 3, 4, 5]
        accessible = await get_accessible_resource_ids(
            user, "order", rbac_service, all_order_ids
        )
        # Use in query: query.filter(Order.id.in_(accessible))
        ```
    """
    accessible = []
    
    for resource_id in candidate_ids:
        if await service.check_resource_ownership(user, resource_type, resource_id):
            accessible.append(resource_id)
    
    return accessible


async def check_bulk_ownership(
    user: UserProtocol,
    resource_type: str,
    service: RBACService,
    resource_ids: List[Any],
) -> dict[Any, bool]:
    """Check ownership for multiple resources at once.
    
    Performs bulk ownership checks and returns a mapping of resource IDs to access status.
    
    Args:
        user: The user to check access for.
        resource_type: Type of resource being checked.
        service: RBACService instance for ownership checks.
        resource_ids: List of resource IDs to check.
        
    Returns:
        dict[Any, bool]: Mapping of resource ID to ownership status.
        
    Example:
        ```python
        ownership_map = await check_bulk_ownership(
            user, "order", rbac_service, [1, 2, 3]
        )
        # {1: True, 2: False, 3: True}
        ```
    """
    results = {}
    
    for resource_id in resource_ids:
        results[resource_id] = await service.check_resource_ownership(
            user, resource_type, resource_id
        )
    
    return results
