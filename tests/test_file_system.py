"""Unit tests for utils/file_system.py"""
import pytest
import openpyxl
from pathlib import Path

from utils.config_io import convert_excel_to_json_data
from utils.file_system import (
    build_report_output_path,
    cleanup_dir,
    create_workspace,
    load_json,
    save_json,
)


class TestCreateWorkspace:
    def test_creates_directory(self, tmp_path):
        ws = create_workspace("my_task", root=tmp_path)
        assert ws.exists()
        assert ws.is_dir()
        assert ws.name == "my_task"

    def test_returns_path_object(self, tmp_path):
        ws = create_workspace("task1", root=tmp_path)
        assert isinstance(ws, Path)

    def test_idempotent(self, tmp_path):
        create_workspace("task1", root=tmp_path)
        create_workspace("task1", root=tmp_path)   # should not raise

    def test_empty_name_raises(self, tmp_path):
        with pytest.raises(ValueError):
            create_workspace("", root=tmp_path)

    def test_whitespace_name_raises(self, tmp_path):
        with pytest.raises(ValueError):
            create_workspace("   ", root=tmp_path)

    def test_strips_whitespace_from_name(self, tmp_path):
        ws = create_workspace("  padded  ", root=tmp_path)
        assert ws.name == "padded"


class TestCleanupDir:
    def test_removes_directory_and_contents(self, tmp_path):
        d = tmp_path / "to_delete"
        d.mkdir()
        (d / "file.txt").write_text("hello")
        cleanup_dir(d)
        assert not d.exists()

    def test_nonexistent_dir_does_not_raise(self, tmp_path):
        cleanup_dir(tmp_path / "ghost")


class TestBuildReportOutputPath:
    def test_builds_reports_path_with_task_report_name(self, tmp_path):
        p = build_report_output_path("my_task", "tag_qa_report.xlsx", root=tmp_path)
        assert p.parent == tmp_path
        assert p.name == "my_task Report.xlsx"

    def test_keeps_spaces_in_task_name(self, tmp_path):
        p = build_report_output_path("My QA Task", "ignored.xlsx", root=tmp_path)
        assert p.name == "My QA Task Report.xlsx"

    def test_ensures_reports_dir_exists(self, tmp_path):
        reports = tmp_path / "Reports"
        p = build_report_output_path("task1", "report.xlsx", root=reports)
        assert reports.exists()
        assert p.parent == reports

    def test_empty_task_name_raises(self, tmp_path):
        with pytest.raises(ValueError):
            build_report_output_path("   ", "report.xlsx", root=tmp_path)

class TestConvertExcelToJsonData:
    def _make_excel(self, tmp_path, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        for row in rows:
            ws.append(row)
        path = str(tmp_path / "kw.xlsx")
        wb.save(path)
        return path

    def test_basic_keywords(self, tmp_path):
        path = self._make_excel(
            tmp_path, [["Keyword"], ["collect"], ["gtm.js"]]
        )
        result = convert_excel_to_json_data(path)
        assert result == ["collect", "gtm.js"]

    def test_empty_rows_skipped(self, tmp_path):
        path = self._make_excel(
            tmp_path, [["Keyword"], ["collect"], [None], ["gtm.js"]]
        )
        result = convert_excel_to_json_data(path)
        assert result == ["collect", "gtm.js"]

    def test_only_header_returns_empty(self, tmp_path):
        path = self._make_excel(tmp_path, [["Keyword"]])
        assert convert_excel_to_json_data(path) == []

    def test_values_are_stripped(self, tmp_path):
        path = self._make_excel(
            tmp_path, [["Keyword"], ["  spaces  "]]
        )
        assert convert_excel_to_json_data(path) == ["spaces"]


class TestSaveLoadJson:
    def test_round_trip(self, tmp_path):
        data = {"key": "value", "nums": [1, 2, 3]}
        p    = tmp_path / "data.json"
        save_json(data, p)
        loaded = load_json(p)
        assert loaded == data

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "nested" / "dir" / "file.json"
        save_json({"x": 1}, p)
        assert p.exists()
