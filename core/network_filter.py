"""
Reusable network-log filtering utilities.

This module is intentionally UI-agnostic:
- Input: keyword identity (num, lang, name) + network event list
- Output: filtered event list, or callback-triggered UI update
"""
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Set


@dataclass(frozen=True)
class KeywordIdentity:
    """Unique keyword key: num + lang + name(text)."""
    num: int
    lang: str
    name: str


@dataclass
class NetworkEvent:
    """One row candidate for the Network panel."""
    name: str
    rtype: str
    status: int
    time_ms: int
    matched: bool
    matched_keywords: Set[KeywordIdentity] = field(default_factory=set)
    source_num: int = 0
    source_lang: str = ""
    source_url: str = ""


def filter_events_for_keyword(
    events: Iterable[NetworkEvent],
    num: int,
    lang: str,
    name: str,
) -> List[NetworkEvent]:
    """
    Return only events matched by the target keyword identity.
    """
    key = KeywordIdentity(num=num, lang=lang, name=name)
    return [event for event in events if key in event.matched_keywords]


def trigger_keyword_filter(
    events: Iterable[NetworkEvent],
    num: int,
    lang: str,
    name: str,
    on_filtered: Callable[[List[NetworkEvent]], None],
) -> None:
    """
    Adapter helper for callers that want filtering to directly trigger a view update.
    """
    on_filtered(filter_events_for_keyword(events, num=num, lang=lang, name=name))

