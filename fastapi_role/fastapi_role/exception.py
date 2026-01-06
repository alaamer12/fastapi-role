import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DatabaseException(Exception):
    """Raised when database operations fail."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class PolicyEvaluationException(Exception):
    """Raised when Casbin policy evaluation fails due to system errors.

    Distinguishes between authorization denial (user lacks permission) and
    system errors (policy engine failure, configuration issues, etc.).
    """

    def __init__(self, error: str, policy_context: Optional[dict[str, Any]] = None):
        """Initialize policy evaluation exception.

        Args:
            error: Description of the policy evaluation error
            policy_context: Optional context about policy state
        """
        self.policy_context = policy_context or {}
        self.message = f"Policy evaluation failed: {error}"  # Add message attribute
        super().__init__(f"Policy evaluation failed: {error}")

        # Log system error for diagnostics
        logger.error(f"Policy evaluation error: {error}, context={policy_context}")
