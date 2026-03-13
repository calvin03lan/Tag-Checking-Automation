"""Unit tests for core/tag_analyzer.py"""
import pytest
from core.tag_analyzer import TagAnalyzer
from models.session import KeywordItem


class TestMatches:
    def test_keyword_present(self):
        assert TagAnalyzer.matches("https://example.com/collect?v=GA4", ["collect"])

    def test_keyword_absent(self):
        assert not TagAnalyzer.matches("https://example.com/page", ["collect"])

    def test_empty_keyword_list(self):
        assert not TagAnalyzer.matches("https://example.com/collect", [])

    def test_empty_string_keyword_ignored(self):
        # Empty string keyword should never trigger a match
        assert not TagAnalyzer.matches("https://example.com/", [""])

    def test_first_of_multiple_keywords_hits(self):
        assert TagAnalyzer.matches("https://example.com/gtm.js", ["gtm", "collect"])

    def test_second_of_multiple_keywords_hits(self):
        assert TagAnalyzer.matches("https://example.com/collect", ["gtm", "collect"])

    def test_none_of_multiple_keywords_hits(self):
        assert not TagAnalyzer.matches("https://example.com/page", ["gtm", "collect"])

    def test_case_sensitive(self):
        # Matching is case-sensitive by design
        assert not TagAnalyzer.matches("https://example.com/COLLECT", ["collect"])


class TestAnalyzeRequests:
    def test_pass_when_one_url_matches(self):
        urls   = ["https://example.com/collect?v=1", "https://other.com/page"]
        passed, matched = TagAnalyzer.analyze_requests(urls, ["collect"])
        assert passed is True
        assert matched == ["https://example.com/collect?v=1"]

    def test_failed_when_no_url_matches(self):
        urls   = ["https://example.com/page", "https://other.com/api"]
        passed, matched = TagAnalyzer.analyze_requests(urls, ["collect"])
        assert passed is False
        assert matched == []

    def test_multiple_matches_returned(self):
        urls = [
            "https://example.com/collect?a=1",
            "https://example.com/collect?b=2",
            "https://other.com/page",
        ]
        passed, matched = TagAnalyzer.analyze_requests(urls, ["collect"])
        assert passed is True
        assert len(matched) == 2

    def test_empty_captured_urls(self):
        passed, matched = TagAnalyzer.analyze_requests([], ["collect"])
        assert passed is False
        assert matched == []

    def test_empty_keywords(self):
        passed, matched = TagAnalyzer.analyze_requests(
            ["https://example.com/collect"], []
        )
        assert passed is False
        assert matched == []

    def test_both_empty(self):
        passed, matched = TagAnalyzer.analyze_requests([], [])
        assert passed is False
        assert matched == []


class TestParameterBasedMatching:
    def test_dc_matches_type_and_cat_parameters(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="dc_cat_1",
            secondary_text="dc_type_a",
            tag_type="dc",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://x.doubleclick.net/activityi?type=dc_type_a&cat=dc_cat_1&ord=1",
            kw,
        )

    def test_dc_does_not_match_if_type_missing(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="dc_cat_1",
            secondary_text="dc_type_a",
            tag_type="dc",
        )
        assert not TagAnalyzer.matches_keyword_item(
            "https://x.doubleclick.net/activityi?cat=dc_cat_1&ord=1",
            kw,
        )

    def test_dc_matches_cat_in_semicolon_path_params(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="dc_cat_1",
            secondary_text="dc_type_a",
            tag_type="dc",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://x.doubleclick.net/activityi;src=123;cat=dc_cat_1;type=dc_type_a;ord=1?gtm=2",
            kw,
        )

    def test_gtag_matches_conversion_id_and_label(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="abc_label",
            secondary_text="16998351256",
            tag_type="gtag",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://www.googleadservices.com/pagead/conversion/16998351256/?label=abc_label",
            kw,
        )

    def test_gtag_does_not_match_if_conversion_id_missing(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="abc_label",
            secondary_text="16998351256",
            tag_type="gtag",
        )
        assert not TagAnalyzer.matches_keyword_item(
            "https://www.googleadservices.com/pagead/conversion/?label=abc_label",
            kw,
        )

    def test_meta_matches_master_pixel_id_and_ev(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="purchase",
            secondary_text="pixel_1",
            tag_type="meta",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://www.facebook.com/tr/?id=pixel_1&ev=purchase",
            kw,
        )

    def test_meta_does_not_match_if_master_pixel_id_missing(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="purchase",
            secondary_text="pixel_1",
            tag_type="meta",
        )
        assert not TagAnalyzer.matches_keyword_item(
            "https://www.facebook.com/tr/?ev=purchase",
            kw,
        )

    def test_ttd_matches_account_id_and_ct(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="ct_123",
            secondary_text="acc_456",
            tag_vendor="ttd",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://insight.adsrvr.org/track?account_id=acc_456&ct=ct_123",
            kw,
        )

    def test_ttd_does_not_match_if_account_id_missing(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="ct_123",
            secondary_text="acc_456",
            tag_vendor="ttd",
        )
        assert not TagAnalyzer.matches_keyword_item(
            "https://insight.adsrvr.org/track?ct=ct_123",
            kw,
        )

    def test_taboola_matches_account_id_and_en(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="en_abc",
            secondary_text="acc_tab_1",
            tag_vendor="taboola",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://trc.taboola.com/?account=acc_tab_1&en=en_abc",
            kw,
        )

    def test_applier_matches_action_and_track(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="track_1",
            secondary_text="action_2",
            tag_vendor="applier",
        )
        assert TagAnalyzer.matches_keyword_item(
            "https://x.example.com/pixel?action_id=action_2&track_id=track_1",
            kw,
        )

    def test_applier_does_not_match_if_action_missing(self):
        kw = KeywordItem(
            num=1,
            lang="en",
            text="track_1",
            secondary_text="action_2",
            tag_vendor="applier",
        )
        assert not TagAnalyzer.matches_keyword_item(
            "https://x.example.com/pixel?track_id=track_1",
            kw,
        )

    def test_other_still_uses_url_contains(self):
        kw = KeywordItem(num=1, lang="en", text="track_id_x", tag_type="other")
        assert TagAnalyzer.matches_keyword_item(
            "https://a.example.com/path/track_id_x?x=1", kw
        )
