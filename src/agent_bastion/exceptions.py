"""
agent_bastion.exceptions — Custom exception hierarchy for the Agent-Bastion Python SDK.
"""

from typing import Optional, Any, Dict


class AgentBastionError(Exception):
    """Base exception class for all exceptions raised by the Agent-Bastion SDK."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AgentBastionError):
    """Raised when API key authentication fails (HTTP 401 Unauthorized or invalid credentials)."""
    pass


class RateLimitError(AgentBastionError):
    """Raised when an API rate limit or tenant quota is exceeded (HTTP 429 Too Many Requests)."""
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, details=details)
        self.retry_after = retry_after


class TenantIsolationError(AgentBastionError):
    """Raised when attempting to access resources across tenant boundaries (HTTP 403 Forbidden)."""
    pass


class TaskExecutionError(AgentBastionError):
    """Raised when an agent session task fails or encounters a browser automation error."""
    pass


class ConnectionError(AgentBastionError):
    """Raised when the SDK cannot establish a network connection with the Agent-Bastion API gateway."""
    pass
