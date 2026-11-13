"""Spread: the client for Bahn's dispatch challenge. See HANDBOOK.md."""
from .client import Client, SpreadError, Unreachable, World

__all__ = ["Client", "SpreadError", "Unreachable", "World"]
__version__ = "0.1.0"
