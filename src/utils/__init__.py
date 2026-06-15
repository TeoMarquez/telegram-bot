# utils/__init__.py

from .auth import authorized_only

from .network import (
    wait_for_internet,
    is_windows,
    get_public_ip
)

from .uptime import get_uptime


__all__ = [
    "authorized_only",

    "wait_for_internet",
    "is_windows",
    "get_public_ip",

    "get_uptime"
]