"""
Persistent login credentials storage for browser authentication.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Dict, Optional

from models.config import OUTPUT_BASE_ROOT
from utils.file_system import load_json, save_json

DEFAULT_LOGIN_CREDENTIALS: Dict[str, str] = {
    "username": "depaemuser",
    "password": "Pr0t8ctd8pa8mus8r",
}


def load_login_credentials(path: Optional[Path] = None) -> Dict[str, str]:
    file_path = _resolve_credentials_path(path)
    if not file_path.exists():
        return copy.deepcopy(DEFAULT_LOGIN_CREDENTIALS)
    try:
        raw = load_json(file_path)
    except Exception:
        return copy.deepcopy(DEFAULT_LOGIN_CREDENTIALS)
    if not isinstance(raw, dict):
        return copy.deepcopy(DEFAULT_LOGIN_CREDENTIALS)
    username = str(raw.get("username", "")).strip()
    password = str(raw.get("password", "")).strip()
    if not username or not password:
        return copy.deepcopy(DEFAULT_LOGIN_CREDENTIALS)
    return {"username": username, "password": password}


def save_login_credentials(credentials: Dict[str, str], path: Optional[Path] = None) -> None:
    username = str(credentials.get("username", "")).strip()
    password = str(credentials.get("password", "")).strip()
    payload = {
        "username": username or DEFAULT_LOGIN_CREDENTIALS["username"],
        "password": password or DEFAULT_LOGIN_CREDENTIALS["password"],
    }
    save_json(payload, _resolve_credentials_path(path))


def _resolve_credentials_path(path: Optional[Path]) -> Path:
    if path is not None:
        return path
    env_path = os.getenv("TAG_QA_LOGIN_CREDENTIALS_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return OUTPUT_BASE_ROOT / "login_credentials.json"
