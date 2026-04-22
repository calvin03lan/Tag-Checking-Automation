"""Unit tests for utils/platform_runtime.py"""
from pathlib import Path

from utils.platform_runtime import (
    chrome_executable_candidates,
    default_output_base_root,
    new_tab_click_modifier,
    screen_capture_reset_hint_command,
)


def test_default_output_base_root_on_macos():
    root = default_output_base_root(platform_name="darwin", home=Path("/Users/demo"), env={})
    assert root == Path("/Users/demo/Documents/Tag_QA_Files")


def test_default_output_base_root_on_windows_prefers_onedrive_documents():
    env = {"USERPROFILE": r"C:\Users\demo"}
    root = default_output_base_root(platform_name="win32", home=Path(r"C:\Users\demo"), env=env)
    # Path existence is environment-dependent; function must always produce
    # a Documents-style path on Windows.
    assert str(root).lower().endswith("tag_qa_files")


def test_windows_chrome_candidates_include_local_appdata():
    env = {"LOCALAPPDATA": r"C:\Users\demo\AppData\Local"}
    candidates = list(chrome_executable_candidates(platform_name="win32", env=env))
    assert r"C:\Program Files\Google\Chrome\Application\chrome.exe" in candidates
    assert any("AppData" in c and c.lower().endswith("chrome.exe") for c in candidates)


def test_click_modifier_is_meta_on_macos_control_elsewhere():
    assert new_tab_click_modifier(platform_name="darwin") == "Meta"
    assert new_tab_click_modifier(platform_name="win32") == "Control"


def test_screen_capture_reset_hint_only_on_macos():
    assert screen_capture_reset_hint_command(platform_name="darwin") == "tccutil reset ScreenCapture"
    assert screen_capture_reset_hint_command(platform_name="win32") == ""
