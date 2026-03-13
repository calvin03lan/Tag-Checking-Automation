"""
Pure, stateless keyword-matching logic.
No I/O, no side-effects — trivially unit-testable.
"""
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, urlsplit

from models.session import KeywordItem


class TagAnalyzer:

    @staticmethod
    def matches(request_url: str, keywords: List[str]) -> bool:
        """Return True if request_url contains at least one non-empty keyword."""
        return any(kw in request_url for kw in keywords if kw)

    @staticmethod
    def analyze_requests(
        captured_urls: List[str],
        keywords: List[str],
    ) -> Tuple[bool, List[str]]:
        """
        Scan captured request URLs against the keyword list.

        Returns:
            (passed, matched_urls)
            passed       – True if at least one request URL matched
            matched_urls – subset of captured_urls that contained a keyword
        """
        matched = [
            url for url in captured_urls
            if TagAnalyzer.matches(url, keywords)
        ]
        return bool(matched), matched

    @staticmethod
    def keyword_statuses(
        captured_urls: List[str],
        keywords: List[str],
    ) -> Dict[str, bool]:
        """
        Return a per-keyword hit map.

        Returns:
            {keyword_text: True/False}
            True  – at least one captured URL contained this keyword
            False – no captured URL contained this keyword
        """
        return {
            kw: any(kw in url for url in captured_urls)
            for kw in keywords
            if kw
        }

    @staticmethod
    def matches_keyword_item(request_url: str, keyword: KeywordItem) -> bool:
        """
        Match one KeywordItem against one request URL.

        Rules:
        - dc    -> query param `cat`
        - gtag  -> query param `label`
        - meta  -> query param `ev`
        - ttd   -> URL contains `account_id + ct`
        - taboola -> URL contains `account_id + en`
        - applier -> URL contains `action_id + track_id`
        - other -> fallback to URL contains keyword text
        """
        if not keyword.text:
            return False

        if keyword.tag_vendor == "doubleclick":
            return _match_doubleclick(request_url, keyword)

        if keyword.tag_vendor == "gtag":
            return _match_gtag(request_url, keyword)

        if keyword.tag_vendor == "meta":
            return _match_meta(request_url, keyword)

        if keyword.tag_vendor == "ttd":
            return _match_ttd(request_url, keyword)

        if keyword.tag_vendor == "taboola":
            return _match_taboola(request_url, keyword)

        if keyword.tag_vendor == "applier":
            return _match_applier(request_url, keyword)

        if keyword.tag_type == "dc":
            return _match_doubleclick(request_url, keyword)

        if keyword.tag_type == "gtag":
            return _match_gtag(request_url, keyword)

        if keyword.tag_type == "meta":
            return _match_meta(request_url, keyword)

        return keyword.text in request_url

    @staticmethod
    def matched_keyword_keys(
        request_url: str,
        keyword_items: List[KeywordItem],
    ) -> List[Tuple[int, str, str]]:
        """Return matched keyword identity keys for one request URL."""
        matched: List[Tuple[int, str, str]] = []
        for keyword in keyword_items:
            if TagAnalyzer.matches_keyword_item(request_url, keyword):
                matched.append((keyword.num, keyword.lang, keyword.text))
        return matched

    @staticmethod
    def analyze_requests_with_items(
        captured_urls: List[str],
        keyword_items: List[KeywordItem],
    ) -> Tuple[bool, List[str]]:
        """Analyze captured URLs using KeywordItem-aware matching rules."""
        matched_urls = [
            url for url in captured_urls
            if TagAnalyzer.matched_keyword_keys(url, keyword_items)
        ]
        return bool(matched_urls), matched_urls


def _extract_param_values(request_url: str, param: str) -> List[str]:
    """
    Extract parameter values from both query and semicolon path params.

    Examples:
    - https://x.com/path?cat=a
    - https://x.doubleclick.net/activityi;src=1;cat=a;type=b
    """
    try:
        parsed = urlsplit(request_url)
    except Exception:
        return []

    target = param.lower()
    values: List[str] = []

    query = parse_qs(parsed.query, keep_blank_values=True)
    for key, vals in query.items():
        if key.lower() == target:
            values.extend([str(v) for v in vals if v is not None])

    for token in parsed.path.split(";"):
        if "=" not in token:
            continue
        key, val = token.split("=", 1)
        if key.strip().lower() == target:
            values.append(val)

    return values


def _param_contains(request_url: str, param: str, expected: str) -> bool:
    if not expected:
        return False
    values = _extract_param_values(request_url, param)
    return any(expected in str(value) for value in values if value is not None)


def _match_doubleclick(request_url: str, keyword: KeywordItem) -> bool:
    if not keyword.secondary_text:
        return False
    has_cat = _param_contains(request_url, "cat", keyword.text)
    has_type = _param_contains(request_url, "type", keyword.secondary_text)
    return has_cat and has_type


def _match_gtag(request_url: str, keyword: KeywordItem) -> bool:
    if not keyword.secondary_text:
        return False
    has_label = _param_contains(request_url, "label", keyword.text) or keyword.text in request_url
    has_conversion_id = keyword.secondary_text in request_url
    return has_label and has_conversion_id


def _match_meta(request_url: str, keyword: KeywordItem) -> bool:
    if not keyword.secondary_text:
        return False
    has_ev = _param_contains(request_url, "ev", keyword.text)
    has_pixel_id = _param_contains(request_url, "id", keyword.secondary_text)
    return has_ev and has_pixel_id


def _match_ttd(request_url: str, keyword: KeywordItem) -> bool:
    return _contains_all(request_url, keyword.secondary_text, keyword.text)


def _match_taboola(request_url: str, keyword: KeywordItem) -> bool:
    return _contains_all(request_url, keyword.secondary_text, keyword.text)


def _match_applier(request_url: str, keyword: KeywordItem) -> bool:
    return _contains_all(
        request_url,
        keyword.secondary_text,
        keyword.text,
    )


def _contains_all(request_url: str, *needles: str | None) -> bool:
    normalized = [str(needle) for needle in needles if needle]
    if not normalized:
        return False
    return all(needle in request_url for needle in normalized)
