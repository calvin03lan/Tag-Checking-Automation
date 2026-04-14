"""
BrowserAutomation — Playwright orchestration layer.

Deliberately imports nothing from tkinter/app/.
All UI communication happens through injected callbacks so this module
stays fully decoupled from the presentation layer.
"""
import asyncio
import os
import re
import shutil
import sys
import tempfile
import time as _time
from datetime import datetime
from typing import Awaitable, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit

from playwright.async_api import BrowserContext, Page, Request, Response, async_playwright

from core.tag_analyzer import TagAnalyzer
from models.config import CLICK_TIMEOUT_MS, PAGE_LOAD_TIMEOUT_MS
from models.session import KeywordItem, ReportEntry, UrlItem, UrlStatus


_RTYPE_MAP = {
    "document":   "Doc",
    "stylesheet": "CSS",
    "image":      "Img",
    "media":      "Media",
    "font":       "Font",
    "script":     "JS",
    "texttrack":  "Text",
    "xhr":        "XHR",
    "fetch":      "Fetch",
    "eventsource":"Event",
    "websocket":  "WS",
    "manifest":   "Manifest",
    "ping":       "Ping",
    "other":      "Other",
}

_MOBILE_EMULATION_PROFILE = {
    # Approximate iPhone 12 viewport/profile for mobile web testing.
    "viewport": {"width": 390, "height": 844},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
    "user_agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
}


def _request_name(url: str) -> str:
    """Return request display name without scheme/domain, keeping path+query."""
    try:
        parsed = urlsplit(url)
        path = parsed.path.lstrip("/")
        query = f"?{parsed.query}" if parsed.query else ""
        name = f"{path}{query}".strip()
        return name if name else parsed.netloc
    except Exception:
        return url


def _get_system_chrome_path() -> Optional[str]:
    """Return the system Chrome executable path, or None if not found."""
    if sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    elif sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    else:
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class BrowserAutomation:
    """
    Runs a Chrome session (incognito, system install) and processes URLs serially.

    Each keyword's ``button_name`` (the element ID) is used to locate a button
    on the page and click it with Cmd/Ctrl so the link opens in a new tab
    without navigating away from the current page.

    Callbacks (all optional, all called from the automation thread):
        on_status_change(url_item, new_status)
        on_log(message)
        on_screenshot(url_item, page_screenshot_path, matched_keys)
            -> {(num, lang, text): stitched_screenshot_path}
        on_progress(completed_count, total_count)
        on_request(name, rtype, status, time_ms, matched, matched_keys)
            ← fires per response
            + current page identity (num, lang, url)
        on_keyword_result(matched_keys, current_num, current_lang)
            ← fires after each URL
    """

    def __init__(
        self,
        keyword_items: List[KeywordItem],
        login_username: str = "",
        login_password: str = "",
        emulate_mobile: bool = False,
        on_status_change: Optional[Callable[[UrlItem, UrlStatus], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_screenshot: Optional[
            Callable[
                [UrlItem, str, List[Tuple[int, str, str]]],
                Dict[Tuple[int, str, str], str],
            ]
        ] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_request: Optional[
            Callable[
                [str, str, int, int, bool, List[Tuple[int, str, str]], int, str, str],
                None,
            ]
        ] = None,
        on_keyword_result: Optional[
            Callable[[Set[Tuple[int, str, str]], int, str], None]
        ] = None,
    ) -> None:
        self.keyword_items = keyword_items
        self.login_username = (login_username or "").strip()
        self.login_password = (login_password or "").strip()
        self.emulate_mobile = emulate_mobile
        self._on_status_change  = on_status_change  or (lambda *_: None)
        self._on_log            = on_log            or (lambda _: None)
        self._on_screenshot = on_screenshot or (lambda *_: {})
        self._on_progress       = on_progress       or (lambda *_: None)
        self._on_request        = on_request        or (lambda *_: None)
        self._on_keyword_result = on_keyword_result or (lambda *_: None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self, urls: List[UrlItem], workspace_path: str
    ) -> List[ReportEntry]:
        """
        Open system Chrome in incognito mode via launch_persistent_context,
        process every URL in order, then close.
        Returns a list of ReportEntry (one per URL).
        """
        entries:      List[ReportEntry] = []
        total         = len(urls)
        user_data_dir = tempfile.mkdtemp()

        try:
            async with async_playwright() as p:
                chrome_path = _get_system_chrome_path()
                if self.emulate_mobile:
                    # Mobile mode uses a non-persistent context to guarantee an
                    # isolated incognito-like session while still applying
                    # viewport/touch/user-agent emulation.
                    launch_options: dict = {
                        "headless": False,
                        "args": ["--incognito"],
                    }
                    if chrome_path:
                        launch_options["executable_path"] = chrome_path
                        self._on_log(f"Using system Chrome: {chrome_path}")
                    else:
                        self._on_log("System Chrome not found — falling back to bundled Chromium")

                    self._on_log(
                        "Using mobile emulation profile in incognito session"
                    )
                    browser = await p.chromium.launch(**launch_options)

                    context_options = dict(_MOBILE_EMULATION_PROFILE)
                    if self.login_username and self.login_password:
                        context_options["http_credentials"] = {
                            "username": self.login_username,
                            "password": self.login_password,
                        }
                        self._on_log(
                            "Using login credentials for browser authentication"
                        )
                    context = await browser.new_context(**context_options)
                    page = await context.new_page()
                else:
                    launch_options = {
                        "headless": False,
                        "args": ["--incognito"],
                    }
                    if self.login_username and self.login_password:
                        launch_options["http_credentials"] = {
                            "username": self.login_username,
                            "password": self.login_password,
                        }
                        self._on_log(
                            "Using login credentials for browser authentication"
                        )
                    if chrome_path:
                        launch_options["executable_path"] = chrome_path
                        self._on_log(f"Using system Chrome: {chrome_path}")
                    else:
                        self._on_log("System Chrome not found — falling back to bundled Chromium")

                    context = await p.chromium.launch_persistent_context(
                        user_data_dir, **launch_options
                    )
                    page = context.pages[0] if context.pages else await context.new_page()

                for idx, url_item in enumerate(urls, start=1):
                    kw_entries = await self._process_url(
                        page, url_item, workspace_path, context, url_seq=idx
                    )
                    entries.extend(kw_entries)
                    self._on_progress(idx, total)

                await context.close()
                if self.emulate_mobile:
                    await browser.close()
        finally:
            shutil.rmtree(user_data_dir, ignore_errors=True)

        return entries

    # ------------------------------------------------------------------
    # Per-URL processing
    # ------------------------------------------------------------------

    async def _process_url(
        self,
        page: Page,
        url_item: UrlItem,
        workspace_path: str,
        context: BrowserContext,
        url_seq: int = 1,
    ) -> List[ReportEntry]:
        """
        Process one URL and return one ReportEntry per keyword.

        *url_seq* is the 1-based iteration index used solely for unique
        screenshot file naming; it is independent of url_item.num.
        """
        captured:      List[str] = []
        pending_times: dict      = {}   # id(request) → monotonic start time
        last_log_event_at        = _time.monotonic()
        req_matched_keys: Dict[int, List[Tuple[int, str, str]]] = {}

        def _on_req(request: Request) -> None:
            nonlocal last_log_event_at
            captured.append(request.url)
            pending_times[id(request)] = _time.monotonic()
            matched_keys = _matched_keyword_keys(request.url)
            if not matched_keys:
                return

            req_matched_keys[id(request)] = matched_keys
            for key in matched_keys:
                key_match_count[key] = key_match_count.get(key, 0) + 1

            # Emit matched request rows immediately so logs are not lost when
            # certain beacons have no usable/visible response phase.
            rtype = _RTYPE_MAP.get(request.resource_type, request.resource_type.upper()[:8])
            self._on_request(
                _request_name(request.url),
                rtype,
                0,   # status unavailable at request phase
                0,   # elapsed unavailable at request phase
                True,
                matched_keys,
                url_item.num,
                url_item.lang,
                url_item.url,
            )
            last_log_event_at = _time.monotonic()

        def _matched_keyword_keys(request_url: str) -> List[Tuple[int, str, str]]:
            return TagAnalyzer.matched_keyword_keys(request_url, self.keyword_items)

        def _on_resp(response: Response) -> None:
            nonlocal last_log_event_at
            req     = response.request
            start   = pending_times.pop(id(req), None)
            elapsed = int((_time.monotonic() - start) * 1000) if start else 0

            name    = _request_name(req.url)
            rtype   = _RTYPE_MAP.get(req.resource_type,
                                     req.resource_type.upper()[:8])
            matched_keys = req_matched_keys.pop(id(req), None)
            if matched_keys is None:
                matched_keys = _matched_keyword_keys(req.url)
            matched      = bool(matched_keys)
            self._on_request(
                name,
                rtype,
                response.status,
                elapsed,
                matched,
                matched_keys,
                url_item.num,
                url_item.lang,
                url_item.url,
            )
            # Every displayed log row refreshes debounce countdown.
            last_log_event_at = _time.monotonic()

        async def _wait_for_log_stable(
            idle_ms: int = 500,
            max_wait_ms: int = 15000,
        ) -> None:
            """
            Debounce countdown:
            every new log event resets timer; timer reaches zero => "stable".
            """
            idle_s = idle_ms / 1000.0
            deadline = _time.monotonic() + (max_wait_ms / 1000.0)
            while True:
                elapsed = _time.monotonic() - last_log_event_at
                remain = idle_s - elapsed
                if remain <= 0:
                    return
                if _time.monotonic() >= deadline:
                    return
                await asyncio.sleep(min(0.05, max(0.01, remain)))

        page.on("request",  _on_req)
        page.on("response", _on_resp)
        self._on_status_change(url_item, UrlStatus.RUNNING)
        self._on_log(f"▶  [{url_item.num}] {url_item.url}")

        screenshot_path: Optional[str] = None
        kw_statuses: dict               = {}
        overall_passed                  = False
        key_match_count: Dict[Tuple[int, str, str], int] = {}

        try:
            page_keywords = self._keywords_for_page(url_item.num, url_item.lang)
            button_ids = self._unique_button_ids(page_keywords)

            await page.goto(
                url_item.url,
                wait_until="domcontentloaded",
                timeout=PAGE_LOAD_TIMEOUT_MS,
            )
            # URL opened; wait until logs become stable before next phase.
            await _wait_for_log_stable(idle_ms=500)
            await self._simulate_interactions(
                page,
                context,
                button_ids=button_ids,
                wait_for_stable=_wait_for_log_stable,
                expected_url=url_item.url,
            )
            await _wait_for_log_stable(idle_ms=500)

            overall_passed, matched_urls = TagAnalyzer.analyze_requests_with_items(
                captured, self.keyword_items
            )
            matched_key_set: Set[Tuple[int, str, str]] = {
                key for key, count in key_match_count.items() if count > 0
            }
            self._on_keyword_result(matched_key_set, url_item.num, url_item.lang)

            # Wait for requests to settle before taking the web snapshot.
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            # Some pages may navigate away after interaction clicks (e.g. promo jump).
            # For evidence consistency, make sure screenshot is captured on the
            # expected current task URL.
            try:
                current_url = page.url
            except Exception:
                current_url = ""
            if current_url and current_url != url_item.url:
                try:
                    await page.goto(
                        url_item.url,
                        wait_until="domcontentloaded",
                        timeout=PAGE_LOAD_TIMEOUT_MS,
                    )
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

            # Bring browser window to front before capturing it
            try:
                await page.bring_to_front()
                await asyncio.sleep(0.3)
            except Exception:
                pass

            # Ensure screenshot is captured from the top of the page.
            try:
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.2)
            except Exception:
                pass

            # Use url_seq (1, 2, 3 …) for unique filenames regardless of url_item.num
            screenshot_path = f"{workspace_path}/screenshot_{url_seq}.png"
            await page.screenshot(path=screenshot_path, full_page=False)

            status = UrlStatus.PASS if overall_passed else UrlStatus.FAILED
            self._on_status_change(url_item, status)

            icon = "✅" if overall_passed else "❌"
            self._on_log(
                f"{icon} [{'PASS' if overall_passed else 'FAILED'}] "
                f"{url_item.url}  hits={matched_urls[:3]}"
            )

        except Exception as exc:
            self._on_log(f"💥 [ERROR] {url_item.url}: {exc}")
            self._on_status_change(url_item, UrlStatus.FAILED)

        finally:
            page.remove_listener("request",  _on_req)
            page.remove_listener("response", _on_resp)

        # Build one ReportEntry per keyword (current page num/lang only).
        tested_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entries: List[ReportEntry] = []
        for kw in self.keyword_items:
            if kw.num != url_item.num or kw.lang != url_item.lang:
                continue
            key = (kw.num, kw.lang, kw.text)
            # PASS criterion: filtered rows exist and therefore are green.
            is_pass = key_match_count.get(key, 0) > 0
            # Keep page snapshot path for post-browser evidence stitching
            # on the UI thread after browser shutdown.
            shot = screenshot_path
            entries.append(ReportEntry(
                url_index=url_item.num,
                url=url_item.url,
                url_lang=url_item.lang,
                kw_num=kw.num,
                kw_text=kw.text,
                kw_lang=kw.lang,
                kw_button=kw.button_name,
                result="PASS" if is_pass else "FAILED",
                tested_at=tested_at,
                screenshot_path=shot,
                tag_vendor=kw.tag_vendor,
                source_row=kw.source_row,
            ))
        return entries

    def _keywords_for_page(self, num: int, lang: str) -> List[KeywordItem]:
        return [kw for kw in self.keyword_items if kw.num == num and kw.lang == lang]

    def _unique_button_ids(self, keywords: List[KeywordItem]) -> List[str]:
        seen: set = set()
        ids: List[str] = []
        for kw in keywords:
            if kw.button_name and kw.button_name not in seen:
                seen.add(kw.button_name)
                ids.append(kw.button_name)
        return ids

    async def _simulate_interactions(
        self,
        page: Page,
        context: BrowserContext,
        button_ids: List[str],
        wait_for_stable: Callable[..., Awaitable[None]],
        expected_url: str,
    ) -> None:
        """
        For current page's deduplicated button IDs:
        - click every 2 seconds with Cmd/Ctrl+left-click (new tab behavior)
        - wait for log debounce timer to reach zero before next step
        """
        modifier = "Meta" if sys.platform == "darwin" else "Control"
        if not button_ids:
            self._on_log("ℹ️  No button IDs for current page; skip click phase")
            return

        async def _detect_overlay_state() -> Dict[str, object]:
            script = """
                () => {
                    const visible = (el) => {
                        if (!el) return false;
                        const s = window.getComputedStyle(el);
                        if (s.display === "none" || s.visibility === "hidden" || s.opacity === "0") return false;
                        const r = el.getBoundingClientRect();
                        return r.width > 12 && r.height > 12;
                    };
                    const selectors = [
                        '[role="dialog"][aria-modal="true"]',
                        '[role="dialog"]',
                        '[aria-modal="true"]',
                        '.modal',
                        '.drawer',
                        '.offcanvas',
                        '[class*="modal"]',
                        '[class*="drawer"]',
                        '[class*="popup"]',
                        '[class*="overlay"]',
                        '[class*="side-panel"]'
                    ];
                    let overlayCount = 0;
                    for (const sel of selectors) {
                        for (const el of document.querySelectorAll(sel)) {
                            if (visible(el)) overlayCount += 1;
                        }
                    }
                    const bodyStyle = window.getComputedStyle(document.body || document.documentElement);
                    const htmlStyle = window.getComputedStyle(document.documentElement);
                    const bodyLocked = (
                        bodyStyle.overflow === "hidden" ||
                        bodyStyle.overflowY === "hidden" ||
                        htmlStyle.overflow === "hidden" ||
                        htmlStyle.overflowY === "hidden"
                    );
                    return { overlayCount, bodyLocked };
                }
            """
            try:
                result = await page.evaluate(script)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
            return {"overlayCount": 0, "bodyLocked": False}

        async def _dismiss_inpage_overlay(stage: str) -> None:
            state = await _detect_overlay_state()
            overlay_count = int(state.get("overlayCount", 0) or 0)
            body_locked = bool(state.get("bodyLocked", False))
            if overlay_count <= 0 and not body_locked:
                return

            self._on_log(
                f"ℹ️  Detected in-page overlay ({stage}): "
                f"overlayCount={overlay_count}, bodyLocked={body_locked}; trying to close"
            )

            # 1) Common escape path for drawers/modals.
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.1)
            except Exception:
                pass

            # 2) Try common close buttons.
            close_selectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="dismiss" i]',
                'button[title*="close" i]',
                'button[title*="dismiss" i]',
                '[data-dismiss]',
                '[data-bs-dismiss]',
                '.btn-close',
                '.modal-close',
                '.drawer-close',
                '.close',
                '[class*="close" i]',
                '[id*="close" i]',
                '[class*="dismiss" i]',
                '[id*="dismiss" i]',
                '[class*="cancel" i]',
                '[id*="cancel" i]',
                '[class*="close-btn" i]',
                '[id*="close-btn" i]',
            ]
            for selector in close_selectors:
                try:
                    loc = page.locator(selector)
                    count = await loc.count()
                    for idx in range(min(count, 6)):
                        btn = loc.nth(idx)
                        try:
                            if await btn.is_visible() and await btn.is_enabled():
                                await btn.click(timeout=1200)
                                await asyncio.sleep(0.1)
                                break
                        except Exception:
                            continue
                except Exception:
                    continue

            # 3) Try text-based close buttons.
            text_patterns = [
                re.compile(r"(close|dismiss|cancel|back|return)", re.I),
                re.compile(r"(關閉|关闭|取消|返回|收起|返回上一頁)"),
            ]
            for pattern in text_patterns:
                try:
                    btn = page.get_by_role("button", name=pattern).first
                    if await btn.count() > 0 and await btn.is_visible() and await btn.is_enabled():
                        await btn.click(timeout=1200)
                        await asyncio.sleep(0.1)
                except Exception:
                    pass

            # 3.5) Fuzzy JS fallback: click topmost visible "close-like" control.
            try:
                clicked = await page.evaluate(
                    """
                    () => {
                        const isVisible = (el) => {
                            if (!el) return false;
                            const s = window.getComputedStyle(el);
                            if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
                            const r = el.getBoundingClientRect();
                            return r.width > 8 && r.height > 8;
                        };
                        const score = (el) => {
                            const t = [
                                el.id || "",
                                el.className || "",
                                el.getAttribute("aria-label") || "",
                                el.getAttribute("title") || "",
                                el.innerText || "",
                            ].join(" ").toLowerCase();
                            let s = 0;
                            if (/close|dismiss|cancel|back|x\\b|關閉|关闭|取消|返回|收起/.test(t)) s += 2;
                            if (/(btn|button|icon|modal|drawer|popup|overlay)/.test(t)) s += 1;
                            return s;
                        };
                        const nodes = Array.from(document.querySelectorAll("button,[role='button'],a,span,div"));
                        const candidates = nodes.filter((el) => {
                            if (!isVisible(el)) return false;
                            return score(el) > 0;
                        });
                        if (!candidates.length) return false;
                        candidates.sort((a, b) => score(b) - score(a));
                        const top = candidates[0];
                        top.click();
                        return true;
                    }
                    """
                )
                if clicked:
                    await asyncio.sleep(0.1)
            except Exception:
                pass

            # 4) Some overlays close when backdrop is clicked.
            try:
                backdrop = page.locator(
                    '.modal-backdrop, .drawer-backdrop, [class*="backdrop"], [class*="overlay-bg"]'
                ).first
                if await backdrop.count() > 0 and await backdrop.is_visible():
                    await backdrop.click(timeout=1200)
                    await asyncio.sleep(0.1)
            except Exception:
                pass

            await wait_for_stable(idle_ms=500)
            after = await _detect_overlay_state()
            after_count = int(after.get("overlayCount", 0) or 0)
            after_locked = bool(after.get("bodyLocked", False))
            if after_count > 0 or after_locked:
                self._on_log(
                    f"⚠️  Overlay may still be open ({stage}): "
                    f"overlayCount={after_count}, bodyLocked={after_locked}"
                )
            else:
                self._on_log(f"✅ Overlay closed ({stage})")

        def _same_target_page(current_url: str, target_url: str) -> bool:
            """
            Compare URL by origin + path, ignoring query/fragment differences.
            """
            try:
                curr = urlsplit(current_url)
                target = urlsplit(target_url)
                curr_path = (curr.path or "/").rstrip("/") or "/"
                target_path = (target.path or "/").rstrip("/") or "/"
                return (
                    curr.scheme == target.scheme
                    and curr.netloc == target.netloc
                    and curr_path == target_path
                )
            except Exception:
                return current_url == target_url

        async def _restore_expected_page_if_drifted() -> None:
            current_url = ""
            try:
                current_url = page.url
            except Exception:
                pass
            if current_url and _same_target_page(current_url, expected_url):
                return
            self._on_log(
                "↩️  Page drift detected after click; "
                f"restoring current test URL: {expected_url}"
            )
            try:
                await page.goto(
                    expected_url,
                    wait_until="domcontentloaded",
                    timeout=PAGE_LOAD_TIMEOUT_MS,
                )
            except Exception as exc:
                self._on_log(f"⚠️  Failed to restore expected URL: {exc}")
                return
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            await wait_for_stable(idle_ms=500)

        async def _pick_clickable_button(
            btn_id: str,
            timeout_s: float = 4.0,
        ) -> Tuple[Optional[object], int]:
            """
            Find a clickable element for the given ID.

            Why:
            - Some pages may contain duplicated IDs where earlier nodes are hidden
              (language variants, template placeholders, etc.).
            - Picking `.first` can falsely report "not visible" even when another
              node with the same ID is visible and clickable.
            """
            locator = page.locator(f'[id="{btn_id}"]')
            deadline = _time.monotonic() + timeout_s
            last_count = 0

            while _time.monotonic() < deadline:
                try:
                    count = await locator.count()
                except Exception:
                    count = 0
                last_count = count
                if count > 0:
                    for idx in range(count):
                        candidate = locator.nth(idx)
                        try:
                            if await candidate.is_visible() and await candidate.is_enabled():
                                return candidate, count
                        except Exception:
                            continue
                await asyncio.sleep(0.1)

            return None, last_count

        async def _pick_clickable_by_fuzzy(btn_id: str) -> Optional[object]:
            """
            Fuzzy fallback when strict ID lookup returns zero elements.

            Why:
            - Some pages don't keep a stable/standard button element.
            - Designers may move identifiers to class/name/aria/text fields.
            """
            token_candidates = [
                token.lower()
                for token in re.split(r"[^A-Za-z0-9]+", btn_id or "")
                if len(token) >= 3
            ]
            if not token_candidates and btn_id:
                token_candidates = [btn_id.lower()]
            if not token_candidates:
                return None

            candidates = page.locator("button, [role='button'], a, div, span, li")
            try:
                count = await candidates.count()
            except Exception:
                return None

            max_scan = min(count, 400)
            for idx in range(max_scan):
                node = candidates.nth(idx)
                try:
                    if not (await node.is_visible() and await node.is_enabled()):
                        continue
                except Exception:
                    continue

                try:
                    attrs = await node.evaluate(
                        """(el) => ({
                            id: el.id || "",
                            className: (typeof el.className === "string" ? el.className : ""),
                            name: el.getAttribute("name") || "",
                            ariaLabel: el.getAttribute("aria-label") || "",
                            title: el.getAttribute("title") || "",
                            text: (el.innerText || el.textContent || "").trim(),
                        })"""
                    )
                except Exception:
                    continue
                haystack = " ".join(
                    [
                        str(attrs.get("id", "")),
                        str(attrs.get("className", "")),
                        str(attrs.get("name", "")),
                        str(attrs.get("ariaLabel", "")),
                        str(attrs.get("title", "")),
                        str(attrs.get("text", "")),
                    ]
                ).lower()
                if not haystack:
                    continue

                if all(token in haystack for token in token_candidates):
                    return node
            return None

        # Heuristic click flow:
        # Some buttons become visible only after prior interactions or after closing
        # blocking overlays. Keep scanning pending IDs and click as soon as available.
        pending: List[str] = list(button_ids)
        clicked: List[str] = []
        idle_rounds = 0
        round_no = 0
        max_rounds = max(4, len(pending) * 3)

        while pending and round_no < max_rounds and idle_rounds < 2:
            round_no += 1
            round_progress = False
            for btn_id in list(pending):
                try:
                    await _restore_expected_page_if_drifted()
                    await _dismiss_inpage_overlay(stage=f"before #{btn_id}")
                    element, total_same_id = await _pick_clickable_button(
                        btn_id,
                        timeout_s=1.8,
                    )
                    if total_same_id == 0:
                        element = await _pick_clickable_by_fuzzy(btn_id)
                        if element is None:
                            continue
                        self._on_log(
                            f"ℹ️  ID #{btn_id} not found; using fuzzy locator fallback"
                        )
                    if element is None:
                        continue

                    try:
                        await element.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    self._on_log(f"🖱  Cmd/Ctrl+left-click #{btn_id}")
                    await element.click(
                        button="left",
                        modifiers=[modifier],
                        timeout=CLICK_TIMEOUT_MS,
                    )
                    await asyncio.sleep(2.0)

                    # Close any new tabs that the click may have opened
                    for extra_page in context.pages:
                        if extra_page != page:
                            await extra_page.close()

                    await _restore_expected_page_if_drifted()
                    await _dismiss_inpage_overlay(stage=f"after #{btn_id}")
                    await wait_for_stable(idle_ms=500)

                    pending.remove(btn_id)
                    clicked.append(btn_id)
                    round_progress = True
                except Exception as exc:
                    self._on_log(f"⚠️  Error clicking #{btn_id}: {exc}")

            if round_progress:
                idle_rounds = 0
                continue

            idle_rounds += 1
            await _restore_expected_page_if_drifted()
            await _dismiss_inpage_overlay(stage=f"round-{round_no}-idle")
            await wait_for_stable(idle_ms=500)

        if pending:
            self._on_log(
                "⚠️  Some button IDs remain unclicked after heuristic retries: "
                f"{pending[:6]}"
            )
