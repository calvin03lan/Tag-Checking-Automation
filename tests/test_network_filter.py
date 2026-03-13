"""Unit tests for core/network_filter.py"""
from core.network_filter import (
    KeywordIdentity,
    NetworkEvent,
    filter_events_for_keyword,
    trigger_keyword_filter,
)


def _ev(name, kws):
    return NetworkEvent(
        name=name,
        rtype="XHR",
        status=200,
        time_ms=10,
        matched=bool(kws),
        matched_keywords=set(kws),
    )


class TestFilterEventsForKeyword:
    def test_filters_by_num_lang_name_triplet(self):
        k1 = KeywordIdentity(num=1, lang="en", name="collect")
        k2 = KeywordIdentity(num=1, lang="tc", name="collect")
        events = [
            _ev("a", [k1]),
            _ev("b", [k2]),
            _ev("c", []),
        ]
        result = filter_events_for_keyword(events, num=1, lang="en", name="collect")
        assert [e.name for e in result] == ["a"]

    def test_returns_empty_when_no_match(self):
        k1 = KeywordIdentity(num=2, lang="en", name="pageview")
        events = [_ev("a", [k1])]
        result = filter_events_for_keyword(events, num=1, lang="en", name="collect")
        assert result == []


class TestTriggerKeywordFilter:
    def test_calls_callback_with_filtered_rows(self):
        k1 = KeywordIdentity(num=1, lang="en", name="collect")
        events = [_ev("a", [k1]), _ev("b", [])]
        received = {}

        def _cb(rows):
            received["rows"] = rows

        trigger_keyword_filter(
            events, num=1, lang="en", name="collect", on_filtered=_cb
        )
        assert [e.name for e in received["rows"]] == ["a"]

