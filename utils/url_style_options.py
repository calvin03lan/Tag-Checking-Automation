"""
Global URL style options storage and URL rebuilding helpers.

Options are persisted across tasks in a JSON file under Tag_QA_Files so that
URL style selections can be reused in later runs.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Dict, List, Optional

from models.config import OUTPUT_BASE_ROOT
from models.session import UrlItem
from utils.file_system import load_json, save_json


DEFAULT_URL_STYLE_OPTIONS: Dict[str, object] = {
    "titles": {
        "pws": ["https://www.hangseng.com"],
        "cms": ["https://cms.hangseng.com"],
    },
    "langs": {
        "pws": {
            "tc": ["/zh-hk"],
            "sc": ["/zh-cn"],
            "en": ["/en-hk"],
        },
        "cms": {
            "tc": ["/chi"],
            "sc": ["/schi"],
            "en": ["/eng"],
        },
    },
    "suffixes": {
        "cms": ["/index.html"],
    },
    "selected": {
        "titles": {
            "pws": "https://www.hangseng.com",
            "cms": "https://cms.hangseng.com",
        },
        "langs": {
            "pws": {"tc": "/zh-hk", "sc": "/zh-cn", "en": "/en-hk"},
            "cms": {"tc": "/chi", "sc": "/schi", "en": "/eng"},
        },
        "suffixes": {
            "cms": "/index.html",
        },
    },
}


def load_url_style_options(path: Optional[Path] = None) -> Dict[str, object]:
    file_path = _resolve_options_path(path)
    if not file_path.exists():
        return copy.deepcopy(DEFAULT_URL_STYLE_OPTIONS)

    try:
        loaded = load_json(file_path)
    except Exception:
        return copy.deepcopy(DEFAULT_URL_STYLE_OPTIONS)

    if not isinstance(loaded, dict):
        return copy.deepcopy(DEFAULT_URL_STYLE_OPTIONS)
    return _normalize_options(loaded)


def save_url_style_options(options: Dict[str, object], path: Optional[Path] = None) -> None:
    file_path = _resolve_options_path(path)
    normalized = _normalize_options(options)
    save_json(normalized, file_path)


def apply_style_to_url_items(
    url_items: List[UrlItem],
    options: Optional[Dict[str, object]] = None,
) -> List[UrlItem]:
    style = _normalize_options(options or load_url_style_options())
    rebuilt: List[UrlItem] = []
    for item in url_items:
        if item.url_kind in {"pws", "cms"} and item.url_path:
            new_url = build_url_from_path(
                url_path=item.url_path,
                lang=item.lang,
                url_kind=item.url_kind,
                options=style,
            )
        else:
            new_url = item.url

        rebuilt.append(
            UrlItem(
                url=new_url,
                lang=item.lang,
                num=item.num,
                status=item.status,
                url_path=item.url_path,
                url_kind=item.url_kind,
            )
        )
    return rebuilt


def build_url_from_path(
    url_path: str,
    lang: str,
    url_kind: str,
    options: Optional[Dict[str, object]] = None,
) -> str:
    style = _normalize_options(options or load_url_style_options())
    kind = url_kind if url_kind in {"pws", "cms"} else "pws"
    lang_key = lang if lang in {"tc", "sc", "en"} else "en"

    title = style["selected"]["titles"][kind]
    lang_seg = style["selected"]["langs"][kind][lang_key]
    path = _normalize_url_path(url_path)

    if kind == "cms":
        suffix = _normalize_cms_suffix(style["selected"]["suffixes"]["cms"])
        return f"{title}{path.rstrip('/')}{lang_seg}{suffix}"
    return f"{title}{lang_seg}{path}"


def _resolve_options_path(path: Optional[Path]) -> Path:
    if path is not None:
        return path
    env_path = os.getenv("TAG_QA_URL_STYLE_OPTIONS_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return OUTPUT_BASE_ROOT / "url_style_options.json"


def _normalize_options(data: Dict[str, object]) -> Dict[str, object]:
    base = copy.deepcopy(DEFAULT_URL_STYLE_OPTIONS)

    titles = _as_dict(data.get("titles"))
    langs = _as_dict(data.get("langs"))
    suffixes = _as_dict(data.get("suffixes"))
    selected = _as_dict(data.get("selected"))
    selected_titles = _as_dict(selected.get("titles"))
    selected_langs = _as_dict(selected.get("langs"))
    selected_suffixes = _as_dict(selected.get("suffixes"))

    for kind in ("pws", "cms"):
        title_list = _as_list(titles.get(kind))
        if title_list:
            base["titles"][kind] = title_list

        sel_title = str(selected_titles.get(kind, "")).strip()
        if sel_title and sel_title in base["titles"][kind]:
            base["selected"]["titles"][kind] = sel_title
        else:
            base["selected"]["titles"][kind] = base["titles"][kind][0]

        lang_lists = _as_dict(langs.get(kind))
        sel_langs = _as_dict(selected_langs.get(kind))
        for lang in ("tc", "sc", "en"):
            seg_list = _as_list(lang_lists.get(lang))
            if seg_list:
                base["langs"][kind][lang] = seg_list

            sel_seg = str(sel_langs.get(lang, "")).strip()
            if sel_seg and sel_seg in base["langs"][kind][lang]:
                base["selected"]["langs"][kind][lang] = sel_seg
            else:
                base["selected"]["langs"][kind][lang] = base["langs"][kind][lang][0]

    cms_suffix_options = _as_list(suffixes.get("cms"), transform=_normalize_cms_suffix)
    if cms_suffix_options:
        base["suffixes"]["cms"] = cms_suffix_options

    selected_cms_suffix = _normalize_cms_suffix(selected_suffixes.get("cms", ""))
    if selected_cms_suffix in base["suffixes"]["cms"]:
        base["selected"]["suffixes"]["cms"] = selected_cms_suffix
    else:
        base["selected"]["suffixes"]["cms"] = base["suffixes"]["cms"][0]

    return base


def _as_dict(value) -> Dict:
    return value if isinstance(value, dict) else {}


def _as_list(value, transform=None) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned: List[str] = []
    for raw in value:
        item = str(raw).strip()
        if not item:
            continue
        if transform is not None:
            item = str(transform(item)).strip()
            if not item:
                continue
        cleaned.append(item)
    deduped: List[str] = []
    seen = set()
    for item in cleaned:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _normalize_url_path(path: str) -> str:
    value = str(path).strip()
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def _normalize_cms_suffix(value: object) -> str:
    suffix = str(value or "").strip()
    if not suffix:
        return "/index.html"
    if suffix.startswith("/") or suffix.startswith("."):
        return suffix
    return f"/{suffix}"
