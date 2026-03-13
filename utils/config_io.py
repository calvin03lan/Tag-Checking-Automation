"""
Backward-compatible config I/O facade.

Excel parsing has been decoupled into `utils/excel_config_adapter.py`.
Keep this module as a stable import path for existing callers/tests.
"""
from typing import List, Tuple

from models.session import KeywordItem, UrlItem
from utils.excel_config_adapter import load_excel_to_models, load_legacy_keywords


def load_excel_config(filepath: str) -> Tuple[List[UrlItem], List[KeywordItem]]:
    return load_excel_to_models(filepath)


def convert_excel_to_json_data(filepath: str) -> List[str]:
    return load_legacy_keywords(filepath)
