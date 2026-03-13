"""
Backward-compatible wrapper for Excel report exporting.
"""
from typing import List

from core.excel_exporter import ExcelReportExporter
from models.session import ReportEntry


class ReportWriter:
    """Compatibility adapter; delegates to ExcelReportExporter."""

    def write(self, entries: List[ReportEntry], output_path: str) -> str:
        return ExcelReportExporter().export(entries, output_path)

    def write_into_input_copy(
        self,
        entries: List[ReportEntry],
        input_excel_path: str,
        output_path: str,
    ) -> str:
        return ExcelReportExporter().export_into_input_copy(
            entries,
            input_excel_path=input_excel_path,
            output_path=output_path,
        )
