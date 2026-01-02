"""Provider implementations for fastapi-role.

This package contains default provider implementations for ownership validation
and other pluggable components.
"""

from fastapi_role.providers.default_ownership import DefaultOwnershipProvider

__all__ = ["DefaultOwnershipProvider"]
