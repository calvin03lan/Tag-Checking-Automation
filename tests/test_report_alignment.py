"""Unit tests for core/report_alignment.py"""

from core.report_alignment import align_entries_to_keywords
from models.session import KeywordItem, ReportEntry


def _kw(
    num=1,
    lang="en",
    text="kw",
    button_name=None,
    tag_vendor="gtag",
    source_row=4,
):
    return KeywordItem(
        num=num,
        lang=lang,
        text=text,
        button_name=button_name,
        tag_vendor=tag_vendor,
        source_row=source_row,
    )


def _entry(
    kw_num=1,
    kw_lang="en",
    kw_text="kw",
    kw_button=None,
    result="PASS",
    tag_vendor="gtag",
    source_row=4,
):
    return ReportEntry(
        url_index=1,
        url="https://example.com",
        url_lang=kw_lang,
        kw_num=kw_num,
        kw_text=kw_text,
        kw_lang=kw_lang,
        kw_button=kw_button,
        result=result,
        tested_at="2026-03-05 12:00:00",
        screenshot_path=None,
        tag_vendor=tag_vendor,
        source_row=source_row,
    )


def test_align_entries_to_keywords_exact_match_order():
    keywords = [
        _kw(num=1, lang="en", text="a", tag_vendor="gtag", source_row=4),
        _kw(num=1, lang="en", text="b", tag_vendor="meta", source_row=4),
    ]
    entries = [
        _entry(kw_num=1, kw_lang="en", kw_text="a", tag_vendor="gtag", source_row=4),
        _entry(kw_num=1, kw_lang="en", kw_text="b", tag_vendor="meta", source_row=4),
    ]

    aligned = align_entries_to_keywords(entries, keywords)

    assert aligned[0] is entries[0]
    assert aligned[1] is entries[1]


def test_align_entries_to_keywords_duplicate_key_consumes_top_to_bottom():
    keywords = [
        _kw(text="same", source_row=7),
        _kw(text="same", source_row=7),
    ]
    first = _entry(kw_text="same", result="PASS", source_row=7)
    second = _entry(kw_text="same", result="FAILED", source_row=7)

    aligned = align_entries_to_keywords([first, second], keywords)

    assert aligned == [first, second]


def test_align_entries_to_keywords_missing_entry_returns_none():
    keywords = [
        _kw(text="exists", source_row=10),
        _kw(text="missing", source_row=10),
    ]
    entries = [_entry(kw_text="exists", source_row=10)]

    aligned = align_entries_to_keywords(entries, keywords)

    assert aligned[0] is not None
    assert aligned[1] is None
