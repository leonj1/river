"""Helper utilities for River."""

import base64
import json
from .types import ResumptionToken


def encode_resumption_token(token: ResumptionToken) -> str:
    """
    Encode a resumption token to base64 string.

    Args:
        token: The resumption token to encode

    Returns:
        Base64-encoded JSON string
    """
    json_str = json.dumps(token)
    return base64.b64encode(json_str.encode("utf-8")).decode("utf-8")


def decode_resumption_token(encoded: str) -> ResumptionToken:
    """
    Decode a resumption token from base64 string.

    Args:
        encoded: Base64-encoded token string

    Returns:
        Decoded resumption token

    Raises:
        ValueError: If token is invalid
    """
    try:
        json_str = base64.b64decode(encoded).decode("utf-8")
        data = json.loads(json_str)
        return ResumptionToken(**data)  # type: ignore
    except Exception as e:
        raise ValueError(f"Invalid resumption token: {e}")
