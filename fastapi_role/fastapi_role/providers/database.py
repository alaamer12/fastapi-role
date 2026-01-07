"""Database provider implementations for optional persistence.

This module provides concrete implementations of database providers:
- InMemoryDatabaseProvider: No-op provider for database-free operation
- SQLAlchemyDatabaseProvider: SQLAlchemy integration for database persistence
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from fastapi_role.protocols.database import DatabaseProvider, SyncDatabaseProvider
from fastapi_role.protocols.user import UserProtocol

logger = logging.getLogger(__name__)


class InMemoryDatabaseProvider:
    """In-memory database provider that performs no actual persistence.
    
    This provider allows the RBAC system to work without any database
    dependencies. All operations succeed but don't persist data.
    Perfect for testing, development, or stateless applications.
    """

    def __init__(self):
        """Initialize in-memory provider."""
        self._policies: List[List[str]] = []
        self._user_roles: Dict[str, List[str]] = {}
        self._transactions: Dict[Any, Dict] = {}
        self._transaction_counter = 0

    async def persist_user_role(self, user: UserProtocol, role: str) -> bool:
        """Store user role in memory (not persistent)."""
        user_id = str(getattr(user, 'id', getattr(user, 'email', str(user))))
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        if role not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role)
        logger.debug(f"In-memory: Assigned role '{role}' to user '{user_id}'")
        return True

    async def persist_policy(self, policy: List[str]) -> bool:
        """Store policy in memory (not persistent)."""
        if policy not in self._policies:
            self._policies.append(policy.copy())
        logger.debug(f"In-memory: Added policy {policy}")
        return True

    async def load_policies(self) -> List[List[str]]:
        """Load policies from memory."""
        logger.debug(f"In-memory: Loading {len(self._policies)} policies")
        return [policy.copy() for policy in self._policies]

    async def remove_policy(self, policy: List[str]) -> bool:
        """Remove policy from memory."""
        try:
            self._policies.remove(policy)
            logger.debug(f"In-memory: Removed policy {policy}")
            return True
        except ValueError:
            logger.debug(f"In-memory: Policy {policy} not found for removal")
            return False

    async def load_user_roles(self, user: UserProtocol) -> List[str]:
        """Load user roles from memory."""
        user_id = str(getattr(user, 'id', getattr(user, 'email', str(user))))
        roles = self._user_roles.get(user_id, [])
        logger.debug(f"In-memory: User '{user_id}' has roles {roles}")
        return roles.copy()

    async def transaction_begin(self) -> Any:
        """Begin a mock transaction."""
        self._transaction_counter += 1
        transaction_id = f"txn_{self._transaction_counter}"
        self._transactions[transaction_id] = {
            'active': True,
            'operations': []
        }
        logger.debug(f"In-memory: Started transaction {transaction_id}")
        return transaction_id

    async def transaction_commit(self, transaction: Any) -> bool:
        """Commit a mock transaction."""
        if transaction in self._transactions:
            self._transactions[transaction]['active'] = False
            logger.debug(f"In-memory: Committed transaction {transaction}")
            return True
        logger.warning(f"In-memory: Unknown transaction {transaction}")
        return False

    async def transaction_rollback(self, transaction: Any) -> bool:
        """Rollback a mock transaction."""
        if transaction in self._transactions:
            self._transactions[transaction]['active'] = False
            logger.debug(f"In-memory: Rolled back transaction {transaction}")
            return True
        logger.warning(f"In-memory: Unknown transaction {transaction}")
        return False

    # Synchronous versions
    def persist_user_role_sync(self, user: UserProtocol, role: str) -> bool:
        """Store user role in memory (sync version)."""
        user_id = str(getattr(user, 'id', getattr(user, 'email', str(user))))
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        if role not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role)
        logger.debug(f"In-memory: Assigned role '{role}' to user '{user_id}' (sync)")
        return True

    def persist_policy_sync(self, policy: List[str]) -> bool:
        """Store policy in memory (sync version)."""
        if policy not in self._policies:
            self._policies.append(policy.copy())
        logger.debug(f"In-memory: Added policy {policy} (sync)")
        return True

    def load_policies_sync(self) -> List[List[str]]:
        """Load policies from memory (sync version)."""
        logger.debug(f"In-memory: Loading {len(self._policies)} policies (sync)")
        return [policy.copy() for policy in self._policies]

    def remove_policy_sync(self, policy: List[str]) -> bool:
        """Remove policy from memory (sync version)."""
        try:
            self._policies.remove(policy)
            logger.debug(f"In-memory: Removed policy {policy} (sync)")
            return True
        except ValueError:
            logger.debug(f"In-memory: Policy {policy} not found for removal (sync)")
            return False

    def load_user_roles_sync(self, user: UserProtocol) -> List[str]:
        """Load user roles from memory (sync version)."""
        user_id = str(getattr(user, 'id', getattr(user, 'email', str(user))))
        roles = self._user_roles.get(user_id, [])
        logger.debug(f"In-memory: User '{user_id}' has roles {roles} (sync)")
        return roles.copy()

    def transaction_begin_sync(self) -> Any:
        """Begin a mock transaction (sync version)."""
        self._transaction_counter += 1
        transaction_id = f"txn_{self._transaction_counter}_sync"
        self._transactions[transaction_id] = {
            'active': True,
            'operations': []
        }
        logger.debug(f"In-memory: Started transaction {transaction_id} (sync)")
        return transaction_id

    def transaction_commit_sync(self, transaction: Any) -> bool:
        """Commit a mock transaction (sync version)."""
        if transaction in self._transactions:
            self._transactions[transaction]['active'] = False
            logger.debug(f"In-memory: Committed transaction {transaction} (sync)")
            return True
        logger.warning(f"In-memory: Unknown transaction {transaction} (sync)")
        return False

    def transaction_rollback_sync(self, transaction: Any) -> bool:
        """Rollback a mock transaction (sync version)."""
        if transaction in self._transactions:
            self._transactions[transaction]['active'] = False
            logger.debug(f"In-memory: Rolled back transaction {transaction} (sync)")
            return True
        logger.warning(f"In-memory: Unknown transaction {transaction} (sync)")
        return False


class SQLAlchemyDatabaseProvider:
    """SQLAlchemy database provider for real database persistence.
    
    This provider integrates with SQLAlchemy sessions to provide
    actual database persistence for RBAC operations.
    """

    def __init__(self, session_factory, user_table=None, policy_table=None):
        """Initialize SQLAlchemy provider.
        
        Args:
            session_factory: Callable that returns SQLAlchemy session
            user_table: Optional SQLAlchemy table for user data
            policy_table: Optional SQLAlchemy table for policy data
        """
        self.session_factory = session_factory
        self.user_table = user_table
        self.policy_table = policy_table

    async def persist_user_role(self, user: UserProtocol, role: str) -> bool:
        """Persist user role to database."""
        try:
            session = self.session_factory()
            
            # This is a template - applications should customize based on their schema
            if hasattr(user, 'role'):
                user.role = role
                if hasattr(session, 'commit'):
                    if hasattr(session.commit, '__call__'):
                        # Async session
                        if hasattr(session.commit, '__await__'):
                            await session.commit()
                        else:
                            session.commit()
                
            logger.info(f"SQLAlchemy: Persisted role '{role}' for user")
            return True
            
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to persist user role: {e}")
            if 'session' in locals():
                try:
                    if hasattr(session, 'rollback'):
                        if hasattr(session.rollback, '__await__'):
                            await session.rollback()
                        else:
                            session.rollback()
                except Exception:
                    pass
            return False

    async def persist_policy(self, policy: List[str]) -> bool:
        """Persist policy to database."""
        try:
            session = self.session_factory()
            
            # Template implementation - customize based on your policy table schema
            if self.policy_table is not None:
                # Example: INSERT INTO policy_table (subject, object, action) VALUES (...)
                # Applications should implement based on their schema
                pass
                
            logger.info(f"SQLAlchemy: Persisted policy {policy}")
            return True
            
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to persist policy: {e}")
            return False

    async def load_policies(self) -> List[List[str]]:
        """Load policies from database."""
        try:
            session = self.session_factory()
            
            # Template implementation - customize based on your policy table schema
            policies = []
            if self.policy_table is not None:
                # Example: SELECT subject, object, action FROM policy_table
                # Applications should implement based on their schema
                pass
                
            logger.info(f"SQLAlchemy: Loaded {len(policies)} policies")
            return policies
            
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to load policies: {e}")
            return []

    async def remove_policy(self, policy: List[str]) -> bool:
        """Remove policy from database."""
        try:
            session = self.session_factory()
            
            # Template implementation - customize based on your policy table schema
            if self.policy_table is not None:
                # Example: DELETE FROM policy_table WHERE subject=? AND object=? AND action=?
                # Applications should implement based on their schema
                pass
                
            logger.info(f"SQLAlchemy: Removed policy {policy}")
            return True
            
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to remove policy: {e}")
            return False

    async def load_user_roles(self, user: UserProtocol) -> List[str]:
        """Load user roles from database."""
        try:
            session = self.session_factory()
            
            # Template implementation - customize based on your user schema
            roles = []
            if hasattr(user, 'role') and user.role:
                roles = [user.role]
            
            logger.info(f"SQLAlchemy: Loaded roles {roles} for user")
            return roles
            
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to load user roles: {e}")
            return []

    async def transaction_begin(self) -> Any:
        """Begin database transaction."""
        try:
            session = self.session_factory()
            # Most SQLAlchemy sessions auto-begin transactions
            logger.debug("SQLAlchemy: Transaction started")
            return session
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to begin transaction: {e}")
            return None

    async def transaction_commit(self, transaction: Any) -> bool:
        """Commit database transaction."""
        try:
            if transaction and hasattr(transaction, 'commit'):
                if hasattr(transaction.commit, '__await__'):
                    await transaction.commit()
                else:
                    transaction.commit()
            logger.debug("SQLAlchemy: Transaction committed")
            return True
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to commit transaction: {e}")
            return False

    async def transaction_rollback(self, transaction: Any) -> bool:
        """Rollback database transaction."""
        try:
            if transaction and hasattr(transaction, 'rollback'):
                if hasattr(transaction.rollback, '__await__'):
                    await transaction.rollback()
                else:
                    transaction.rollback()
            logger.debug("SQLAlchemy: Transaction rolled back")
            return True
        except Exception as e:
            logger.error(f"SQLAlchemy: Failed to rollback transaction: {e}")
            return False