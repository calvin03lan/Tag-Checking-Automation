"""
Report-entry alignment helpers.

Keep row-alignment business rules in core layer so UI only orchestrates calls.
"""
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from models.session import KeywordItem, ReportEntry


def align_entries_to_keywords(
    entries: List[ReportEntry],
    keyword_items: List[KeywordItem],
) -> List[Optional[ReportEntry]]:
    """
    Align report entries to keyword row indices.

    Why:
    - Matching only by (num/lang/text) is ambiguous when duplicate keywords exist.
    - Screenshot/filter steps must select each keyword row exactly once, top-to-bottom.
    """
    buckets: Dict[Tuple[int, str, str, Optional[str], str, int], Deque[ReportEntry]] = {}
    for entry in entries:
        key = (
            entry.kw_num,
            entry.kw_lang,
            entry.kw_text,
            entry.kw_button,
            entry.tag_vendor,
            entry.source_row,
        )
        buckets.setdefault(key, deque()).append(entry)

    aligned: List[Optional[ReportEntry]] = []
    for kw in keyword_items:
        key = (
            kw.num,
            kw.lang,
            kw.text,
            kw.button_name,
            kw.tag_vendor,
            kw.source_row,
        )
        bucket = buckets.get(key)
        aligned.append(bucket.popleft() if bucket else None)
    return aligned
