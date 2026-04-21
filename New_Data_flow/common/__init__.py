"""Expose top-level `common` package as `New_Data_flow.common`."""

from importlib import import_module

_common_pkg = import_module("common")

__path__ = _common_pkg.__path__
__all__ = getattr(_common_pkg, "__all__", [])
