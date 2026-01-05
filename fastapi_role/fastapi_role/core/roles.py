"""Role factory and registry system for dynamic role definitions.

This module provides the tools to create Enum-based roles at runtime,
enabling users to define their own roles without modifying library source.
It also includes a registry to track valid roles throughout the application.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional, Set, Type

from fastapi_role.core.composition import RoleComposition


class RoleRegistry:
    """Registry for managing active system roles.

    This class maintains a set of valid role names and the Enum class
    used to represent them. It provides validation and introspection.

    Attributes:
        _roles (Set[str]): Set of registered role values (lowercase).
        _role_enum (Optional[Type[Enum]]): The registered Role Enum class.
    """

    _roles: Set[str] = set()
    _role_enum: Optional[Type[Enum]] = None

    @classmethod
    def register(cls, role_enum: Type[Enum]) -> None:
        """Registers a Role Enum class with the system.

        Extracts all enum values and stores them for validation.

        Args:
            role_enum (Type[Enum]): The Enum class containing role definitions.
        """
        cls._role_enum = role_enum
        cls._roles = {r.value for r in role_enum}

    @classmethod
    def is_valid(cls, role_name: str) -> bool:
        """Checks if a given role name is registered.

        Args:
            role_name (str): The name of the role to validate.

        Returns:
            bool: True if the role is valid, False otherwise.
        """
        return role_name in cls._roles

    @classmethod
    def get_roles(cls) -> Set[str]:
        """Returns all registered role names.

        Returns:
            Set[str]: A set of all registered role values.
        """
        return cls._roles.copy()


def _role_or(self: Enum, other: Any) -> RoleComposition:
    """Implements bitwise OR for Role Enums.

    Enables syntax like: Role.ADMIN | Role.USER

    Args:
        self (Enum): The current role.
        other (Any): The role or composition to combine with.

    Returns:
        RoleComposition: A new composition containing both roles.

    Raises:
        NotImplementedError: If combined with an unsupported type.
    """
    if isinstance(other, RoleComposition):
        return RoleComposition({self} | other.roles)
    elif isinstance(other, Enum):
        return RoleComposition({self, other})
    return NotImplemented


def _role_ror(self: Enum, other: Any) -> RoleComposition:
    """Implements reverse bitwise OR for Role Enums.

    Args:
        self (Enum): The current role.
        other (Any): The role or composition to combine with.

    Returns:
        RoleComposition: A new composition containing both roles.
    """
    if isinstance(other, RoleComposition):
        return RoleComposition(other.roles | {self})
    elif isinstance(other, Enum):
        return RoleComposition({other, self})
    return NotImplemented


# noinspection PyUnresolvedReferences
def create_roles(names: List[str]) -> Type[Enum]:
    """Creates a dynamic Role Enum from a list of names.

    Generates an Enum class where keys are uppercase and values are lowercase.
    Bitwise OR operators are injected to support RoleComposition.

    Args:
        names (List[str]): A list of role names (e.g., ["ADMIN", "USER"]).

    Returns:
        Type[Enum]: A new Enum class with the specified roles.

    Example:
        >>> Role = create_roles(["ADMIN", "USER"])
        >>> Role.ADMIN.value
        'admin'
        >>> isinstance(Role.ADMIN | Role.USER, RoleComposition)
        True
    """
    # Create Enum dictionary
    # Values match the lowercase version of the name for consistency
    enum_dict = {name.upper(): name.lower() for name in names}

    # Create the Enum class
    Role = Enum("Role", enum_dict)  # type: ignore

    # Inject bitwise operators to support composition
    setattr(Role, "__or__", _role_or)
    setattr(Role, "__ror__", _role_ror)

    # Register the new role type globally
    RoleRegistry.register(Role)

    return Role
