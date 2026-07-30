"""Soft bus package — Windows CI default transport."""

from .bus import SoftBus
from .messages import *  # noqa: F403

__all__ = ["SoftBus"]
