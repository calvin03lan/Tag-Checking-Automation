"""
macOS screen-capture permission helpers.

These wrappers use CoreGraphics APIs when available:
- CGPreflightScreenCaptureAccess
- CGRequestScreenCaptureAccess

On non-macOS platforms (or when APIs are unavailable), they return True
so callers can proceed without platform-specific branching.
"""
from __future__ import annotations

from utils.platform_runtime import is_macos


def is_screen_capture_allowed() -> bool:
    if not is_macos():
        return True
    api = _load_coregraphics_api()
    if api is None:
        return True
    preflight = getattr(api, "CGPreflightScreenCaptureAccess", None)
    if preflight is None:
        return True
    preflight.restype = _ctypes().c_bool
    preflight.argtypes = []
    try:
        return bool(preflight())
    except Exception:
        return True


def request_screen_capture_access() -> bool:
    if not is_macos():
        return True
    api = _load_coregraphics_api()
    if api is None:
        return True
    request = getattr(api, "CGRequestScreenCaptureAccess", None)
    if request is None:
        return is_screen_capture_allowed()
    request.restype = _ctypes().c_bool
    request.argtypes = []
    try:
        return bool(request())
    except Exception:
        return is_screen_capture_allowed()


def _load_coregraphics_api():
    try:
        ctypes = _ctypes()
        util = _ctypes_util()
        lib_path = util.find_library("ApplicationServices")
        if not lib_path:
            return None
        return ctypes.CDLL(lib_path)
    except Exception:
        return None


def _ctypes():
    import ctypes

    return ctypes


def _ctypes_util():
    import ctypes.util

    return ctypes.util
