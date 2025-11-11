"""Tests for River error handling."""

import pytest
from river_core.errors import RiverError, RiverErrorType


def test_river_error_creation():
    """Test creating River errors."""
    error = RiverError(
        message="Test error",
        error_type=RiverErrorType.VALIDATION,
        details={"field": "value"},
    )

    assert error.message == "Test error"
    assert error.error_type == RiverErrorType.VALIDATION
    assert error.details == {"field": "value"}


def test_river_error_serialization():
    """Test error serialization."""
    error = RiverError(
        message="Test error",
        error_type=RiverErrorType.PROVIDER,
        details={"key": "value"},
    )

    serialized = error.to_dict()

    assert serialized["message"] == "Test error"
    assert serialized["error_type"] == "PROVIDER"
    assert serialized["details"]["key"] == "value"


def test_river_error_deserialization():
    """Test error deserialization."""
    data = {
        "message": "Test error",
        "error_type": "RUNNER_ERROR",
        "details": {"info": "test"},
    }

    error = RiverError.from_dict(data)

    assert error.message == "Test error"
    assert error.error_type == RiverErrorType.RUNNER_ERROR
    assert error.details["info"] == "test"


def test_river_error_types():
    """Test all error types are defined."""
    types = [
        RiverErrorType.UNKNOWN,
        RiverErrorType.VALIDATION,
        RiverErrorType.PROVIDER,
        RiverErrorType.STREAM_NOT_FOUND,
        RiverErrorType.INVALID_RESUMPTION_TOKEN,
        RiverErrorType.RUNNER_ERROR,
        RiverErrorType.NETWORK,
    ]

    for error_type in types:
        error = RiverError("test", error_type)
        assert error.error_type == error_type
