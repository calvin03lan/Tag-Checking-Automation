"""Unit tests for models/session.py"""
import pytest
from models.session import ReportEntry, Session, UrlItem, UrlStatus


class TestUrlItem:
    def test_default_status_is_standby(self):
        item = UrlItem(url="https://example.com", lang="en", num=1)
        assert item.status == UrlStatus.STANDBY

    def test_status_can_be_overridden(self):
        item = UrlItem(url="https://example.com", lang="en", num=1,
                       status=UrlStatus.PASS)
        assert item.status == UrlStatus.PASS

    def test_fields_stored_correctly(self):
        item = UrlItem(url="https://test.com", lang="tc", num=5)
        assert item.url  == "https://test.com"
        assert item.lang == "tc"
        assert item.num  == 5


class TestUrlStatus:
    def test_string_values(self):
        assert UrlStatus.STANDBY == "STANDBY"
        assert UrlStatus.RUNNING == "RUNNING"
        assert UrlStatus.PASS    == "PASS"
        assert UrlStatus.FAILED  == "FAILED"

    def test_is_string_subclass(self):
        assert isinstance(UrlStatus.PASS, str)


class TestReportEntry:
    def test_all_fields(self):
        entry = ReportEntry(
            url_index=1,
            url="https://example.com",
            url_lang="en",
            kw_num=1,
            kw_text="gtm_click",
            kw_lang="en",
            kw_button="btn-submit",
            result="PASS",
            tested_at="2024-01-01 12:00:00",
            screenshot_path="/tmp/shot.png",
        )
        assert entry.url_index       == 1
        assert entry.kw_text         == "gtm_click"
        assert entry.result          == "PASS"
        assert entry.screenshot_path == "/tmp/shot.png"

    def test_screenshot_path_defaults_to_none(self):
        entry = ReportEntry(
            url_index=1, url="https://example.com", url_lang="en",
            kw_num=1, kw_text="gtm_click", kw_lang="en",
            kw_button=None, result="FAILED", tested_at="2024-01-01 12:00:00",
        )
        assert entry.screenshot_path is None

    def test_kw_button_optional(self):
        entry = ReportEntry(
            url_index=2, url="https://example.com/tc", url_lang="tc",
            kw_num=2, kw_text="some_tag", kw_lang="tc",
            kw_button=None, result="PASS", tested_at="2024-01-01 12:00:00",
        )
        assert entry.kw_button is None


class TestSession:
    def test_default_empty_collections(self):
        session = Session(task_name="test", workspace_path="/tmp/test")
        assert session.urls           == []
        assert session.keywords       == []
        assert session.report_entries == []

    def test_mutable_defaults_are_independent(self):
        s1 = Session(task_name="a", workspace_path="/tmp/a")
        s2 = Session(task_name="b", workspace_path="/tmp/b")
        s1.keywords.append("kw")
        assert s2.keywords == []

    def test_task_name_stored(self):
        session = Session(task_name="my_task", workspace_path="/tmp/ws")
        assert session.task_name == "my_task"
