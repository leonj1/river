"""Error types for River."""

from typing import Any, Literal
from enum import Enum


class RiverErrorType(str, Enum):
    """Types of River errors."""

    UNKNOWN = "UNKNOWN"
    VALIDATION = "VALIDATION"
    PROVIDER = "PROVIDER"
    STREAM_NOT_FOUND = "STREAM_NOT_FOUND"
    INVALID_RESUMPTION_TOKEN = "INVALID_RESUMPTION_TOKEN"
    RUNNER_ERROR = "RUNNER_ERROR"
    NETWORK = "NETWORK"


class RiverError(Exception):
    """River error with type and serialization support."""

    def __init__(
        self,
        message: str,
        error_type: RiverErrorType = RiverErrorType.UNKNOWN,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "message": self.message,
            "error_type": self.error_type.value,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RiverError":
        """Deserialize from dictionary."""
        return cls(
            message=data["message"],
            error_type=RiverErrorType(data["error_type"]),
            details=data.get("details", {}),
        )

    def __repr__(self) -> str:
        return f"RiverError(type={self.error_type.value}, message={self.message})"
