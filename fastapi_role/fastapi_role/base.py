"""Base service class for business logic.

This module provides the base service class that all service classes
should inherit from. Supports both synchronous and asynchronous
SQLAlchemy sessions.

Public Classes:
    BaseService: Base class for all services

Features:
    - Database session management (sync and async)
    - Common service patterns
    - Transaction handling
"""

from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

__all__ = ["BaseService"]


class BaseService:
    """Base service class for business logic.

    Provides common functionality for all service classes including
    database session management and transaction handling.
    
    Supports both synchronous and asynchronous SQLAlchemy sessions.
    Use async methods (commit, rollback, refresh) with AsyncSession.
    Use sync methods (commit_sync, rollback_sync, refresh_sync) with Session.

    Attributes:
        db: Database session for operations (AsyncSession or Session)
    """

    def __init__(self, db: Union[AsyncSession, Session]) -> None:
        """Initialize base service.

        Args:
            db: Database session (AsyncSession or Session)
        """
        self.db = db
        self._is_async = isinstance(db, AsyncSession)

    async def commit(self) -> None:
        """Commit current transaction (async sessions only).
        
        For synchronous sessions, use commit_sync() instead.

        Raises:
            RuntimeError: If called with a synchronous session
            DatabaseException: If commit fails
        """
        if not self._is_async:
            raise RuntimeError(
                "Cannot use async commit() with synchronous session. "
                "Use commit_sync() instead."
            )
        
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            from fastapi_role.exception import DatabaseException

            # Log the actual error for debugging
            print(f"[ERROR] Commit failed: {type(e).__name__}: {str(e)}")
            import traceback

            traceback.print_exc()

            raise DatabaseException(
                message="Failed to commit transaction",
                details={"error": str(e), "type": type(e).__name__},
            ) from e

    def commit_sync(self) -> None:
        """Commit current transaction (sync sessions only).
        
        For asynchronous sessions, use await commit() instead.

        Raises:
            RuntimeError: If called with an asynchronous session
            DatabaseException: If commit fails
        """
        if self._is_async:
            raise RuntimeError(
                "Cannot use sync commit_sync() with asynchronous session. "
                "Use await commit() instead."
            )
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            from fastapi_role.exception import DatabaseException

            # Log the actual error for debugging
            print(f"[ERROR] Commit failed: {type(e).__name__}: {str(e)}")
            import traceback

            traceback.print_exc()

            raise DatabaseException(
                message="Failed to commit transaction",
                details={"error": str(e), "type": type(e).__name__},
            ) from e

    async def rollback(self) -> None:
        """Rollback current transaction (async sessions only).
        
        For synchronous sessions, use rollback_sync() instead.
        
        Raises:
            RuntimeError: If called with a synchronous session
        """
        if not self._is_async:
            raise RuntimeError(
                "Cannot use async rollback() with synchronous session. "
                "Use rollback_sync() instead."
            )
        await self.db.rollback()

    def rollback_sync(self) -> None:
        """Rollback current transaction (sync sessions only).
        
        For asynchronous sessions, use await rollback() instead.
        
        Raises:
            RuntimeError: If called with an asynchronous session
        """
        if self._is_async:
            raise RuntimeError(
                "Cannot use sync rollback_sync() with asynchronous session. "
                "Use await rollback() instead."
            )
        self.db.rollback()

    async def refresh(self, instance) -> None:
        """Refresh instance from database (async sessions only).
        
        For synchronous sessions, use refresh_sync() instead.

        Args:
            instance: SQLAlchemy model instance to refresh
            
        Raises:
            RuntimeError: If called with a synchronous session
        """
        if not self._is_async:
            raise RuntimeError(
                "Cannot use async refresh() with synchronous session. "
                "Use refresh_sync() instead."
            )
        await self.db.refresh(instance)

    def refresh_sync(self, instance) -> None:
        """Refresh instance from database (sync sessions only).
        
        For asynchronous sessions, use await refresh() instead.

        Args:
            instance: SQLAlchemy model instance to refresh
            
        Raises:
            RuntimeError: If called with an asynchronous session
        """
        if self._is_async:
            raise RuntimeError(
                "Cannot use sync refresh_sync() with asynchronous session. "
                "Use await refresh() instead."
            )
        self.db.refresh(instance)
