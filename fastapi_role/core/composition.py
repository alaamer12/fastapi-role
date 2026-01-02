"""Module for handling role compositions.

This module provides the RoleComposition class, which allows multiple roles
to be combined using bitwise operators, forming complex authorization requirements.
"""

from __future__ import annotations
from enum import Enum
from typing import Set, Any, Iterator


class RoleComposition:
    """Represents a set of combined roles.

    Enables bitwise OR operations for roles to create composite requirements.
    Supports nesting and chaining of roles and compositions.

    Attributes:
        roles (Set[Enum]): The set of Enum members included in this composition.
    """

    def __init__(self, roles: Set[Enum]):
        """Initializes the RoleComposition.

        Args:
            roles (Set[Enum]): A set of Enum roles to include.
        """
        self.roles = roles

    def __or__(self, other: Any) -> RoleComposition:
        """Combines this composition with another role or composition.

        Args:
            other (Any): A Role Enum or another RoleComposition.

        Returns:
            RoleComposition: A new combined composition.
        """
        if isinstance(other, RoleComposition):
            return RoleComposition(self.roles | other.roles)
        elif isinstance(other, Enum):
            return RoleComposition(self.roles | {other})
        return NotImplemented

    def __ror__(self, other: Any) -> RoleComposition:
        """Handles right-side combination (Enum | RoleComposition).

        Args:
            other (Any): A Role Enum.

        Returns:
            RoleComposition: A new combined composition.
        """
        if isinstance(other, Enum):
            return RoleComposition({other} | self.roles)
        return NotImplemented

    def __contains__(self, item: Any) -> bool:
        """Checks if a specific role exists within the composition.

        Args:
            item (Any): The role to check for.

        Returns:
            bool: True if the role is present, False otherwise.
        """
        return item in self.roles

    def __iter__(self) -> Iterator[Enum]:
        """Provides an iterator over the roles in the composition.

        Returns:
            Iterator[Enum]: An iterator of Enum roles.
        """
        return iter(self.roles)

    def __repr__(self) -> str:
        """Returns a string representation of the composition.

        Returns:
            str: Representation showing the contained role values.
        """
        role_names = [r.value for r in self.roles]
        return f"RoleComposition({role_names})"
