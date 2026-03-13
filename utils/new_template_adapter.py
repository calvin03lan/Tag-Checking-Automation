"""
Adapter for the client's newer one-sheet Excel template.

This parser converts the new template directly into in-memory model objects,
so callers can keep using existing backend logic without generating any
intermediate legacy Excel files.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from models.config import LANG_COMPAT_MAP, LANG_MAP
from models.session import KeywordItem, UrlItem
from utils.url_style_options import build_url_from_path


HEADER_ROW = 3
DATA_START_ROW = 4
_LANG_ALL = "__all__"

_DEFAULT_LANG_ORDER = ["tc", "sc", "en"]


@dataclass(frozen=True)
class ParsedRow:
    row_index: int
    lang: str
    url_path: str
    button_id: Optional[str]
    is_event: bool
    required_flags: Dict[str, bool]
    keywords: Dict[str, Optional[str]]
    secondary_keywords: Dict[str, Optional[str]]


class NewTemplateConfigAdapter:
    """
    Parse the client's new single-sheet template into UrlItem/KeywordItem.
    """

    def load_to_models(self, ws) -> Tuple[List[UrlItem], List[KeywordItem]]:
        self._validate_header_row_exists(ws)
        column_map = self._resolve_columns_by_fuzzy_header(ws)
        parsed_rows = self._parse_rows_with_validation(ws, column_map)
        return self._build_models(parsed_rows)

    def _validate_header_row_exists(self, ws) -> None:
        if ws.max_row < HEADER_ROW:
            raise ValueError(f"Worksheet has no header row {HEADER_ROW}")

    def _parse_rows_with_validation(
        self,
        ws,
        column_map: Dict[str, int],
    ) -> List[ParsedRow]:
        parsed: List[ParsedRow] = []
        composite_key_to_row: Dict[Tuple[str, str, str], int] = {}

        for row in range(DATA_START_ROW, ws.max_row + 1):
            raw_lang = ws.cell(row=row, column=column_map["language"]).value
            raw_url = ws.cell(row=row, column=column_map["url_path"]).value
            raw_button = ws.cell(row=row, column=column_map["button_id"]).value

            lang = _normalize_lang_or_all(raw_lang)
            url_path = _clean_text(raw_url)
            button_id = _clean_text(raw_button) or None

            # Treat rows without URL path as non-data rows (notes/separators).
            if not url_path:
                continue

            if not lang:
                raise ValueError(
                    f"Row {row}: K(language) and L(URL path) are required for non-empty rows"
                )

            key = (lang, url_path, button_id or "")
            if key in composite_key_to_row:
                first_row = composite_key_to_row[key]
                raise ValueError(
                    "Duplicate composite key detected (K/L/P). "
                    f"Rows: {first_row} and {row}, key={key}"
                )
            composite_key_to_row[key] = row

            is_event = (
                _clean_text(
                    ws.cell(row=row, column=column_map["page_or_event"]).value
                ).lower()
                == "event"
            )
            required_flags = {
                "doubleclick": _is_required(
                    ws.cell(row=row, column=column_map["required_doubleclick"]).value
                ),
                "gtag": _is_required(
                    ws.cell(row=row, column=column_map["required_gtag"]).value
                ),
                "meta": _is_required(
                    ws.cell(row=row, column=column_map["required_meta"]).value
                ),
                "ttd": _is_required(
                    ws.cell(row=row, column=column_map["required_ttd"]).value
                ),
                "taboola": _is_required(
                    ws.cell(row=row, column=column_map["required_taboola"]).value
                ),
                "applier": _is_required(
                    ws.cell(row=row, column=column_map["required_applier"]).value
                ),
            }
            gtag_id, gtag_label = _split_gtag_keyword(
                ws.cell(row=row, column=column_map["keyword_gtag"]).value
            )
            keywords = {
                "doubleclick": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_doubleclick_cat"]).value
                )
                or None,
                "gtag": gtag_label or None,
                "meta": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_meta"]).value
                )
                or None,
                "ttd": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_ttd"]).value
                )
                or None,
                "taboola": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_taboola"]).value
                )
                or None,
                "applier": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_applier"]).value
                )
                or None,
            }
            secondary_keywords = {
                "doubleclick": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_doubleclick_type"]).value
                )
                or None,
                "gtag": gtag_id or None,
                "meta": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_meta_master_id"]).value
                )
                or None,
                "ttd": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_ttd_account_id"]).value
                )
                or None,
                "taboola": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_taboola_account_id"]).value
                )
                or None,
                "applier": _clean_text(
                    ws.cell(row=row, column=column_map["keyword_applier_action_id"]).value
                )
                or None,
            }
            parsed.append(
                ParsedRow(
                    row_index=row,
                    lang=lang,
                    url_path=url_path,
                    button_id=button_id,
                    is_event=is_event,
                    required_flags=required_flags,
                    keywords=keywords,
                    secondary_keywords=secondary_keywords,
                )
            )

        return parsed

    def _build_models(
        self,
        rows: Sequence[ParsedRow],
    ) -> Tuple[List[UrlItem], List[KeywordItem]]:
        url_items: List[UrlItem] = []
        keyword_items: List[KeywordItem] = []

        url_to_num: Dict[Tuple[str, str], int] = {}
        row_lang_to_num: Dict[Tuple[int, str], int] = {}
        for row in rows:
            is_cms = _is_cms_url_path(row.url_path)
            url_kind = "cms" if is_cms else "pws"
            for lang in _expand_languages(row.lang):
                full_url = build_url_from_path(
                    url_path=row.url_path,
                    lang=lang,
                    url_kind=url_kind,
                )
                url_key = (lang, full_url)
                if url_key not in url_to_num:
                    num = len(url_to_num) + 1
                    url_to_num[url_key] = num
                    url_items.append(
                        UrlItem(
                            url=full_url,
                            lang=lang,
                            num=num,
                            url_path=row.url_path,
                            url_kind=url_kind,
                        )
                    )
                row_lang_to_num[(row.row_index, lang)] = url_to_num[url_key]

        seen_keyword_rows: set[
            Tuple[int, str, str, Optional[str], Optional[str], Optional[str], str]
        ] = set()
        for row in rows:
            for lang in _expand_languages(row.lang):
                url_num = row_lang_to_num[(row.row_index, lang)]
                button_name = row.button_id if row.is_event else None

                for vendor, required in row.required_flags.items():
                    if not required:
                        continue
                    keyword = row.keywords.get(vendor)
                    if not keyword:
                        raise ValueError(
                            f"Row {row.row_index}: {vendor} is Required but main keyword is empty"
                        )
                    secondary_keyword = row.secondary_keywords.get(vendor)
                    if _vendor_requires_secondary_keyword(vendor) and not secondary_keyword:
                        raise ValueError(
                            f"Row {row.row_index}: {vendor} is Required but secondary keyword is empty"
                        )
                    normalized_keyword = _normalize_keyword_by_vendor(vendor, keyword)
                    normalized_secondary = _clean_text(secondary_keyword) or None
                    item = (
                        url_num,
                        lang,
                        normalized_keyword,
                        normalized_secondary,
                        None,
                        button_name,
                        vendor,
                    )
                    if item in seen_keyword_rows:
                        continue
                    seen_keyword_rows.add(item)
                    keyword_items.append(
                        KeywordItem(
                            num=url_num,
                            lang=lang,
                            text=normalized_keyword,
                            secondary_text=normalized_secondary,
                            tertiary_text=None,
                            button_name=button_name,
                            tag_type=_tag_type_from_vendor(vendor),
                            tag_vendor=vendor,
                            source_row=row.row_index,
                        )
                    )

        return url_items, keyword_items

    def _resolve_columns_by_fuzzy_header(self, ws) -> Dict[str, int]:
        headers: Dict[int, str] = {}
        for col in range(1, ws.max_column + 1):
            value = ws.cell(row=HEADER_ROW, column=col).value
            if value is None:
                continue
            text = _normalize_header_text(value)
            if text:
                headers[col] = text

        required_fields: Dict[str, List[Callable[[str], bool]]] = {
            "required_doubleclick": [lambda h: "doubleclick" in h],
            "required_gtag": [lambda h: "gtag" in h],
            "required_meta": [lambda h: "meta" in h],
            "required_ttd": [lambda h: "the trade desk" in h or "trade desk" in h],
            "required_taboola": [lambda h: "taboola" in h],
            "required_applier": [
                lambda h: "applier" in h,
                lambda h: "appier" in h,
            ],
            "page_or_event": [lambda h: "page or event" in h],
            "language": [lambda h: "language" in h],
            "url_path": [
                lambda h: "url path name" in h,
                lambda h: "url path" in h and "name" in h,
            ],
            "button_id": [lambda h: "button id" in h],
            "keyword_doubleclick_type": [
                lambda h: "group tag string" in h and "type" in h,
            ],
            "keyword_doubleclick_cat": [
                lambda h: "cat" in h and "tag string" in h,
                lambda h: "activity tag string" in h,
            ],
            "keyword_gtag": [
                lambda h: "gtag event snippet" in h,
                lambda h: "conversion label" in h,
            ],
            "keyword_meta_master_id": [lambda h: "master pixel id" in h],
            "keyword_meta": [lambda h: "ev value" in h],
            "keyword_ttd": [lambda h: "ct value" in h],
            "keyword_taboola": [lambda h: "en value" in h],
            "keyword_applier": [
                lambda h: "track_id" in h,
                lambda h: "track id" in h,
            ],
        }

        resolved: Dict[str, int] = {}
        for field, matchers in required_fields.items():
            col = _find_first_matching_column(headers, matchers)
            if col is None:
                raise ValueError(
                    f"Cannot locate required column for '{field}' by fuzzy header matching"
                )
            resolved[field] = col

        resolved["keyword_ttd_account_id"] = max(1, resolved["keyword_ttd"] - 1)
        resolved["keyword_taboola_account_id"] = max(1, resolved["keyword_taboola"] - 1)
        resolved["keyword_applier_action_id"] = max(1, resolved["keyword_applier"] - 1)
        return resolved


def _find_first_matching_column(
    headers: Dict[int, str],
    matchers: Sequence[Callable[[str], bool]],
) -> Optional[int]:
    for matcher in matchers:
        for col in sorted(headers):
            if matcher(headers[col]):
                return col
    return None


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_required(value: object) -> bool:
    return _clean_text(value).lower() == "required"


def _normalize_header_text(value: object) -> str:
    text = _clean_text(value).lower()
    text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
    return text


def _normalize_lang(raw_lang: object) -> str:
    raw = _clean_text(raw_lang)
    for cand in _lang_lookup_candidates(raw):
        if cand in LANG_COMPAT_MAP:
            return LANG_COMPAT_MAP[cand]
    return LANG_MAP.get(raw, "en")


def _normalize_lang_or_all(raw_lang: object) -> str:
    raw = _clean_text(raw_lang).lower()
    if raw in {"all", "(all)"}:
        return _LANG_ALL
    return _normalize_lang(raw_lang)


def _normalize_keyword_by_vendor(vendor: str, keyword: str) -> str:
    return _clean_text(keyword)


def _vendor_requires_secondary_keyword(vendor: str) -> bool:
    return vendor in {"doubleclick", "gtag", "meta", "ttd", "taboola", "applier"}


def _split_gtag_keyword(value: object) -> Tuple[str, str]:
    text = _clean_text(value)
    if not text:
        return "", ""
    if "/" not in text:
        return "", text
    left, right = text.split("/", 1)
    return left.strip(), right.strip()


def _tag_type_from_vendor(vendor: str) -> str:
    if vendor == "doubleclick":
        return "dc"
    if vendor == "gtag":
        return "gtag"
    if vendor == "meta":
        return "meta"
    if vendor == "ttd":
        return "ttd"
    if vendor == "taboola":
        return "taboola"
    if vendor == "applier":
        return "applier"
    return "other"


def _expand_languages(lang: str) -> List[str]:
    if lang == _LANG_ALL:
        return list(_DEFAULT_LANG_ORDER)
    return [lang]


def _is_cms_url_path(url_path: str) -> bool:
    return "/cms" in url_path.lower()


def _lang_lookup_candidates(raw: str) -> List[str]:
    if not raw:
        return [""]
    base = raw.strip().lower().lstrip("/")
    variants = [
        base,
        base.replace("_", "-"),
        base.replace("-", "_"),
        base.replace(" ", "-"),
        base.replace(" ", "_"),
        base.replace(" ", ""),
    ]
    return list(dict.fromkeys(variants))
