"""FastAPI adapter for River - SSE streaming endpoints."""

from .server import river_endpoint_handler
from .client import create_river_client

__version__ = "0.1.0"

__all__ = [
    "river_endpoint_handler",
    "create_river_client",
]
