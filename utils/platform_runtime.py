"""
Platform-runtime helpers.

This module centralizes OS-specific behavior so the rest of the codebase can
stay platform-agnostic.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Mapping, Optional


def is_macos(platform_name: Optional[str] = None) -> bool:
    return (platform_name or sys.platform) == "darwin"


def is_windows(platform_name: Optional[str] = None) -> bool:
    return (platform_name or sys.platform) == "win32"


def default_output_base_root(
    platform_name: Optional[str] = None,
    home: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    platform_value = platform_name or sys.platform
    home_dir = home or Path.home()
    env_map = env or os.environ

    if is_macos(platform_value):
        return home_dir / "Documents" / "Tag_QA_Files"
    if is_windows(platform_value):
        docs_dir = _windows_documents_dir(home_dir, env_map)
        return docs_dir / "Tag_QA_Files"
    return home_dir / "Tag_QA_Files"


def find_system_chrome_executable(
    platform_name: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[str]:
    for candidate in chrome_executable_candidates(platform_name=platform_name, env=env):
        if os.path.exists(candidate):
            return candidate
    return None


def chrome_executable_candidates(
    platform_name: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Iterable[str]:
    platform_value = platform_name or sys.platform
    env_map = env or os.environ

    if is_macos(platform_value):
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    if is_windows(platform_value):
        local_app_data = env_map.get("LOCALAPPDATA", "").strip()
        local_candidate = (
            Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe"
            if local_app_data
            else None
        )
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        if local_candidate is not None:
            candidates.append(str(local_candidate))
        return candidates
    return [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
    ]


def new_tab_click_modifier(platform_name: Optional[str] = None) -> str:
    return "Meta" if is_macos(platform_name) else "Control"


def screen_capture_reset_hint_command(platform_name: Optional[str] = None) -> str:
    return "tccutil reset ScreenCapture" if is_macos(platform_name) else ""


def _windows_documents_dir(home_dir: Path, env: Mapping[str, str]) -> Path:
    user_profile = env.get("USERPROFILE", "").strip()
    candidates = []
    if user_profile:
        profile_path = Path(user_profile)
        candidates.append(profile_path / "OneDrive" / "Documents")
        candidates.append(profile_path / "Documents")
    candidates.append(home_dir / "Documents")
    candidates.append(home_dir)

    for path in candidates:
        if path.exists():
            return path
    return candidates[0]
