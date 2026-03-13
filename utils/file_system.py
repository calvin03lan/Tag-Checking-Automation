"""
File-system utilities: workspace management and JSON helpers.

Excel / config I/O has been moved to utils/config_io.py which is solely
responsible for translating between external file formats and the app's
data models.  This module contains no format-parsing logic.
"""
import json
import shutil
from pathlib import Path
from typing import Optional

from models.config import DEFAULT_WORKSPACE_ROOT, REPORTS_ROOT


def create_workspace(task_name: str, root: Optional[Path] = None) -> Path:
    """
    Create and return a workspace directory for the given task name.

    Args:
        task_name: Human-readable name; used as the directory name.
        root:      Parent directory (defaults to DEFAULT_WORKSPACE_ROOT).

    Raises:
        ValueError: if task_name is empty or whitespace-only.
    """
    if not task_name or not task_name.strip():
        raise ValueError("task_name must not be empty")

    base      = root or DEFAULT_WORKSPACE_ROOT
    workspace = base / task_name.strip()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def build_report_output_path(
    task_name: str,
    filename: str = "",
    root: Optional[Path] = None,
) -> Path:
    """
    Build report output path under Tag_QA_Files/Reports.
    """
    if not task_name or not task_name.strip():
        raise ValueError("task_name must not be empty")
    reports_root = root or REPORTS_ROOT
    reports_root.mkdir(parents=True, exist_ok=True)
    safe_task = task_name.strip()
    return reports_root / f"{safe_task} Report.xlsx"


def cleanup_dir(path: Path) -> None:
    """Remove a directory tree; silently no-ops if it does not exist."""
    if path.exists() and path.is_dir():
        shutil.rmtree(path)



def save_json(data: object, path: Path) -> None:
    """Serialize *data* as JSON to *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> object:
    """Deserialize JSON from *path*."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
