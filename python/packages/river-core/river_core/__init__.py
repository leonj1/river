"""River Core - Durable, resumable streams for Python."""

from .stream import create_river_stream
from .router import create_river_router
from .callers import create_server_side_caller, create_client_side_caller
from .provider import RiverProvider, default_river_provider
from .errors import RiverError, RiverErrorType
from .types import (
    RiverStream,
    RiverRouter,
    StreamContext,
    StreamHelper,
    CallerStreamItem,
    RiverSpecialChunk,
    ResumptionToken,
)

__version__ = "0.1.0"

__all__ = [
    # Main API
    "create_river_stream",
    "create_river_router",
    "create_server_side_caller",
    "create_client_side_caller",
    # Provider
    "RiverProvider",
    "default_river_provider",
    # Errors
    "RiverError",
    "RiverErrorType",
    # Types
    "RiverStream",
    "RiverRouter",
    "StreamContext",
    "StreamHelper",
    "CallerStreamItem",
    "RiverSpecialChunk",
    "ResumptionToken",
]
