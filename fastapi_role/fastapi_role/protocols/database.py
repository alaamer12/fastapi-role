"""Database provider protocols for optional persistence operations.

This module defines the database provider protocols for optional database
operations. The core RBAC system works without any database dependencies,
but applications can use these providers for persistence needs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Union

from fastapi_role.protocols.user import UserProtocol


class DatabaseProvider(Protocol):
    """Protocol for optional database operations.
    
    This provider allows applications to integrate database persistence
    with the RBAC system while keeping the core engine database-agnostic.
    All methods are optional - the core RBAC works without any database.
    """

    async def persist_user_role(self, user: UserProtocol, role: str) -> bool:
        """Persist user role assignment to database.
        
        Args:
            user: The user whose role is being assigned.
            role: The role name being assigned.
            
        Returns:
            bool: True if persistence succeeded, False otherwise.
        """
        ...

    async def persist_policy(self, policy: List[str]) -> bool:
        """Persist a policy rule to database.
        
        Args:
            policy: The policy rule as a list of strings.
            
        Returns:
            bool: True if persistence succeeded, False otherwise.
        """
        ...

    async def load_policies(self) -> List[List[str]]:
        """Load all policy rules from database.
        
        Returns:
            List[List[str]]: List of policy rules.
        """
        ...

    async def remove_policy(self, policy: List[str]) -> bool:
        """Remove a policy rule from database.
        
        Args:
            policy: The policy rule to remove.
            
        Returns:
            bool: True if removal succeeded, False otherwise.
        """
        ...

    async def load_user_roles(self, user: UserProtocol) -> List[str]:
        """Load user's roles from database.
        
        Args:
            user: The user to load roles for.
            
        Returns:
            List[str]: List of role names for the user.
        """
        ...

    async def transaction_begin(self) -> Any:
        """Begin a database transaction.
        
        Returns:
            Any: Transaction context or identifier.
        """
        ...

    async def transaction_commit(self, transaction: Any) -> bool:
        """Commit a database transaction.
        
        Args:
            transaction: Transaction context from transaction_begin().
            
        Returns:
            bool: True if commit succeeded, False otherwise.
        """
        ...

    async def transaction_rollback(self, transaction: Any) -> bool:
        """Rollback a database transaction.
        
        Args:
            transaction: Transaction context from transaction_begin().
            
        Returns:
            bool: True if rollback succeeded, False otherwise.
        """
        ...


class SyncDatabaseProvider(Protocol):
    """Synchronous version of DatabaseProvider.
    
    For applications that need synchronous database operations.
    """

    def persist_user_role(self, user: UserProtocol, role: str) -> bool:
        """Persist user role assignment to database (sync).
        
        Args:
            user: The user whose role is being assigned.
            role: The role name being assigned.
            
        Returns:
            bool: True if persistence succeeded, False otherwise.
        """
        ...

    def persist_policy(self, policy: List[str]) -> bool:
        """Persist a policy rule to database (sync).
        
        Args:
            policy: The policy rule as a list of strings.
            
        Returns:
            bool: True if persistence succeeded, False otherwise.
        """
        ...

    def load_policies(self) -> List[List[str]]:
        """Load all policy rules from database (sync).
        
        Returns:
            List[List[str]]: List of policy rules.
        """
        ...

    def remove_policy(self, policy: List[str]) -> bool:
        """Remove a policy rule from database (sync).
        
        Args:
            policy: The policy rule to remove.
            
        Returns:
            bool: True if removal succeeded, False otherwise.
        """
        ...

    def load_user_roles(self, user: UserProtocol) -> List[str]:
        """Load user's roles from database (sync).
        
        Args:
            user: The user to load roles for.
            
        Returns:
            List[str]: List of role names for the user.
        """
        ...

    def transaction_begin(self) -> Any:
        """Begin a database transaction (sync).
        
        Returns:
            Any: Transaction context or identifier.
        """
        ...

    def transaction_commit(self, transaction: Any) -> bool:
        """Commit a database transaction (sync).
        
        Args:
            transaction: Transaction context from transaction_begin().
            
        Returns:
            bool: True if commit succeeded, False otherwise.
        """
        ...

    def transaction_rollback(self, transaction: Any) -> bool:
        """Rollback a database transaction (sync).
        
        Args:
            transaction: Transaction context from transaction_begin().
            
        Returns:
            bool: True if rollback succeeded, False otherwise.
        """
        ...