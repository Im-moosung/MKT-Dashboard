"""Expose top-level `channels` package as `New_Data_flow.channels`."""

from importlib import import_module

_channels_pkg = import_module("channels")

__path__ = _channels_pkg.__path__
__all__ = getattr(_channels_pkg, "__all__", [])
