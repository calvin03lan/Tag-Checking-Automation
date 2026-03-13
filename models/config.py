from pathlib import Path

APP_NAME = "Tagging Automation QA"

LANG_MAP = {
    "Traditional Chinese": "tc",
    "Simplified Chinese": "sc",
    "English": "en",
}
LANG_MAP_INV = {v: k for k, v in LANG_MAP.items()}
LANG_OPTIONS = list(LANG_MAP.keys())

# Global language compatibility aliases.
# Canonical codes:
# - Traditional Chinese: tc
# - Simplified Chinese: sc
# - English: en
LANG_ALIAS_GROUPS = {
    "tc": (
        "tc", "chi", "zht", "cht", "zh-hk", "zh-tw", "zh-hant",
        "traditional chinese", "traditional-chinese",
    ),
    "sc": (
        "sc", "schi", "zhs", "chs", "zh-cn", "zh-sg", "zh-hans",
        "simplified chinese", "simplified-chinese",
    ),
    "en": (
        "en", "eng", "en-hk", "en-us", "en-gb",
        "english",
    ),
}
LANG_COMPAT_MAP = {
    alias.lower(): canonical
    for canonical, aliases in LANG_ALIAS_GROUPS.items()
    for alias in aliases
}

REPORT_FILENAME = "tag_qa_report.xlsx"
OUTPUT_BASE_ROOT = Path.home() / "Documents" / "Tag_QA_Files"
PICTURES_ROOT = OUTPUT_BASE_ROOT / "Pictures"
REPORTS_ROOT = OUTPUT_BASE_ROOT / "Reports"

# Keep existing create_workspace() contract, but default picture workspace now
# follows Tag_QA_Files/Pictures/<task_name>.
DEFAULT_WORKSPACE_ROOT = PICTURES_ROOT

# Playwright timeouts (ms)
PAGE_LOAD_TIMEOUT_MS = 30_000
CLICK_TIMEOUT_MS = 2_000
