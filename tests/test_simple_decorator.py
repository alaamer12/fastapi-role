#!/usr/bin/env python3

import asyncio

from fastapi_role import require, create_roles
from tests.conftest import TestUser as User


async def test_simple_decorator():
    """Test simple decorator logic without Hypothesis."""

    # Create user with salesman role
    user = User()
    user.id = 1
    user.email = "test@example.com"
    user.role = "salesman"

    Role = create_roles(["ADMIN", "USER"])

    # Create function with multiple @require decorators (OR logic)
    @require(Role.ADMIN)  # First requirement
    @require(Role.USER)  # Second requirement (OR logic)
    async def test_function(user: User):
        return "success"

    print(f"User role: {user.role}")
    print("Expected: Should pass because user is salesman")

    try:
        result = await test_function(user)
        print(f"Result: {result}")
        print("SUCCESS: Decorator worked correctly")
    except Exception as e:
        print(f"FAILED: {e}")
        return False

    return True


if __name__ == "__main__":
    asyncio.run(test_simple_decorator())
