from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


@dataclass
class KeywordItem:
    num: int
    lang: str               # "sc" | "tc" | "en"
    text: str               # keyword string to match in network requests
    secondary_text: Optional[str] = None  # secondary keyword for compound matching
    tertiary_text: Optional[str] = None   # third keyword for compound matching
    button_name: Optional[str] = None   # associated button trigger, if any
    tag_type: str = "other"            # "dc" | "gtag" | "meta" | "other"
    tag_vendor: str = "other"          # doubleclick|gtag|meta|ttd|taboola|applier|other
    source_row: int = 0                 # original row index in new template


class UrlStatus(str, Enum):
    STANDBY = "STANDBY"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAILED = "FAILED"


@dataclass
class UrlItem:
    url: str
    lang: str   # "sc" | "tc" | "en"
    num: int
    status: UrlStatus = UrlStatus.STANDBY
    url_path: Optional[str] = None  # raw path from template L column
    url_kind: str = "legacy"       # "pws" | "cms" | "legacy"


@dataclass
class ReportEntry:
    """One row in the report = one keyword result for one URL."""
    url_index: int              # URL num as written in the Excel config
    url: str
    url_lang: str               # "sc" | "tc" | "en"
    kw_num: int                 # keyword number
    kw_text: str                # keyword string
    kw_lang: str                # "sc" | "tc" | "en"
    kw_button: Optional[str]    # button element ID (may be None)
    result: str                 # "PASS" | "FAILED"
    tested_at: str
    screenshot_path: Optional[str] = None
    tag_vendor: str = "other"  # doubleclick|gtag|meta|ttd|taboola|applier|other
    source_row: int = 0          # original row index in new template


@dataclass
class Session:
    task_name: str
    workspace_path: str
    urls: List[UrlItem] = field(default_factory=list)
    keywords: List[KeywordItem] = field(default_factory=list)
    report_entries: List[ReportEntry] = field(default_factory=list)
