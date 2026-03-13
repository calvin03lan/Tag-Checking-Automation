"""
MainWindow — the application's top-level UI class.

Layout
------
┌──────────────────────────────────────────────────────────────────┐
│  [Configuration bar]                                             │
├──────────────────────────────────────────────────────────────────┤
│  URL:  [1][en] https://...   ▼  (read-only combobox)            │
├──────────────────────┬───────────────────────────────────────────┤
│  Keywords            │  Network Requests (DevTools-style)        │
│  #│Lang│Tag│Text1│Text2│Btn│Stat │  Seq│Method│ Request URL │ Match │
│  1│ tc │kw1 │ — │PASS │   1│ GET  │ https://...        │  ✓     │
│  …                   │  …                                        │
├──────────────────────┴───────────────────────────────────────────┤
│  [Progress ═══════════════════════════════════]  [▶ Start]       │
├──────────────────────────────────────────────────────────────────┤
│  Console Log  (DevTools-style)                                   │
└──────────────────────────────────────────────────────────────────┘
"""
import asyncio
import os
import re
import time
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter.font as tkfont
from typing import Deque, Dict, List, Optional, Set, Tuple

import tkinter as tk
from tkinter import ttk

import app.styles as S
from app.components.login_manager import LoginManagerDialog
from app.components.url_manager import UrlManagerDialog
from core.automation import BrowserAutomation
from core.network_filter import (
    KeywordIdentity,
    NetworkEvent,
    trigger_keyword_filter,
)
from core.report_alignment import align_entries_to_keywords
from core.reporter import ReportWriter
from models.config import APP_NAME, LANG_MAP_INV
from models.session import KeywordItem, ReportEntry, UrlItem, UrlStatus
from utils.excel_config_adapter import load_excel_to_models
from utils.file_system import build_report_output_path, create_workspace
from utils.image_processor import stitch_side_by_side
from utils.login_credentials import load_login_credentials, save_login_credentials
from utils.screen_capture_permission import (
    is_screen_capture_allowed,
    request_screen_capture_access,
)
from utils.url_style_options import apply_style_to_url_items

# ── Log level detection ──────────────────────────────────────────────
_LEVEL_RULES = [
    ("PASS",    ("✅", "[PASS]")),
    ("FAILED",  ("❌", "[FAILED]")),
    ("ERROR",   ("💥", "[ERROR]", "error", "Error")),
    ("RUNNING", ("▶", "[RUNNING]")),
]
_LOG_BG      = "#1E2430"
_LOG_ROW_ALT = "#242C3A"
_LOG_FG      = {
    "INFO":    "#8B95A5",
    "RUNNING": "#5B9BF0",
    "PASS":    "#4EC94E",
    "FAILED":  "#F05B5B",
    "ERROR":   "#F0A24E",
}

# ── Network panel colours ────────────────────────────────────────────
_NET_BG       = "#FFFFFF"
_NET_BG_ALT   = "#F8F9FA"
_NET_BG_MATCH = "#E6F4EA"   # light green for matched requests
_NET_FG       = "#202124"
_NET_FG_MATCH = "#137333"

# ── Keyword status colours ───────────────────────────────────────────
_KW_STATUS_COLORS = {
    "STANDBY": S.COLOR_STANDBY,
    "PASS":    S.COLOR_PASS,
    "FAILED":  S.COLOR_FAILED,
}


def _detect_level(message: str) -> str:
    for level, markers in _LEVEL_RULES:
        if any(m in message for m in markers):
            return level
    return "INFO"


class MainWindow:

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1240x730")
        self.root.configure(bg=S.COLOR_BG)

        S.configure_styles(ttk.Style(self.root))

        # ── App state ────────────────────────────────────────────────
        self._urls:           List[UrlItem]     = []
        self._keyword_items:  List[KeywordItem] = []
        self._excel_path:     Optional[str]     = None
        self._workspace:      Optional[Path]    = None
        self._is_running:     bool              = False
        self._login_credentials: Dict[str, str] = load_login_credentials()

        # Treeview iid trackers
        self._kw_iid_list:   List[str] = []   # index → kw treeview iid
        self._net_row_count: int       = 0
        self._log_row_count: int       = 0
        self._all_network_events: List[NetworkEvent] = []
        self._displayed_network_events: Dict[str, NetworkEvent] = {}
        self._current_filter: Optional[KeywordIdentity] = None
        self._net_text_filter_var = tk.StringVar(value="")
        self._pending_network_rows: Deque[
            Tuple[str, str, int, int, bool, List[Tuple[int, str, str]], int, str, str]
        ] = deque()
        self._net_flush_scheduled: bool = False

        self._build_ui()

    # ================================================================
    # UI construction
    # ================================================================

    def _build_ui(self) -> None:
        self._build_config_bar()
        self._build_url_selector()
        self._build_center_panels()
        self._build_progress_bar()
        self._build_log_panel()

    # ── Config bar ───────────────────────────────────────────────────
    def _build_config_bar(self) -> None:
        cfg = ttk.LabelFrame(self.root, text="Configuration", padding=8)
        cfg.pack(fill=tk.X, padx=10, pady=(8, 3))

        ttk.Label(cfg, text="Task Name:").grid(row=0, column=0, sticky=tk.W)
        self._task_name_var = tk.StringVar(
            value=f"Task_{datetime.now().strftime('%Y%m%d_%H%M')}"
        )
        ttk.Entry(cfg, textvariable=self._task_name_var, width=72).grid(
            row=0, column=1, padx=(4, 10), sticky=tk.EW
        )

        ttk.Button(cfg, text="Browse…",
                   command=self._load_excel).grid(row=0, column=2, padx=4)
        ttk.Button(cfg, text="Manage URLs",
                   command=self._open_url_manager).grid(row=0, column=3, padx=6)
        ttk.Button(cfg, text="Login Management",
                   command=self._open_login_manager).grid(row=0, column=4, padx=6)

        cfg.grid_columnconfigure(1, weight=1)

    # ── URL selector (single combobox) ───────────────────────────────
    def _build_url_selector(self) -> None:
        row = ttk.Frame(self.root)
        row.pack(fill=tk.X, padx=10, pady=(0, 3))

        self._summary_var = tk.StringVar(value="URLs: 0  |  Keywords: 0")
        ttk.Label(
            row, textvariable=self._summary_var,
            foreground=S.COLOR_TEXT_LIGHT, font=S.FONT_SMALL,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row, text="URL:").pack(side=tk.LEFT)
        self._url_combo_var = tk.StringVar()
        self._url_combo = ttk.Combobox(
            row, textvariable=self._url_combo_var,
            state="readonly", font=S.FONT_BODY,
        )
        self._url_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    # ── Center: Keywords (left) + Network requests (right) ───────────
    def _build_center_panels(self) -> None:
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=0)
        self._center_paned = paned

        # ── Left: Keywords panel ─────────────────────────────────────
        kw_frame = ttk.LabelFrame(paned, text="Keywords", padding=4)
        paned.add(kw_frame, weight=11)
        self._kw_frame = kw_frame

        _kw_style = ttk.Style()
        _kw_style.configure(
            "Kw.Treeview",
            background=_NET_BG,
            fieldbackground=_NET_BG,
            foreground=_NET_FG,
            rowheight=18,
            font=("Courier", 8),
        )
        _kw_style.configure(
            "Kw.Treeview.Heading",
            background="#F1F3F4",
            foreground="#5F6368",
            font=("Helvetica", 8, "bold"),
        )

        self._kw_cols = ("#", "Lang", "Tag", "Text1", "Text2", "Button", "Status")
        self._kw_tree = ttk.Treeview(
            kw_frame, columns=self._kw_cols, show="headings", style="Kw.Treeview"
        )
        self._kw_tree.heading("#",      text="#",      anchor=tk.CENTER)
        self._kw_tree.heading("Lang",   text="Lang",   anchor=tk.CENTER)
        self._kw_tree.heading("Tag",    text="Tag",    anchor=tk.CENTER)
        self._kw_tree.heading("Text1",  text="Text1",  anchor=tk.W)
        self._kw_tree.heading("Text2",  text="Text2",  anchor=tk.W)
        self._kw_tree.heading("Button", text="ID", anchor=tk.W)
        self._kw_tree.heading("Status", text="Status", anchor=tk.CENTER)
        self._kw_tree.column("#",      width=30,  anchor=tk.CENTER, stretch=False)
        self._kw_tree.column("Lang",   width=36,  anchor=tk.CENTER, stretch=False)
        self._kw_tree.column("Tag",    width=48,  anchor=tk.CENTER, stretch=False)
        self._kw_tree.column("Text1",  width=108, anchor=tk.W)
        self._kw_tree.column("Text2",  width=116, anchor=tk.W)
        self._kw_tree.column("Button", width=92,  anchor=tk.W)
        self._kw_tree.column("Status", width=60,  anchor=tk.CENTER, stretch=False)

        for tag, colour in _KW_STATUS_COLORS.items():
            self._kw_tree.tag_configure(tag, background=colour)

        kw_vsb = ttk.Scrollbar(kw_frame, orient="vertical",
                               command=self._kw_tree.yview)
        self._kw_tree.configure(yscrollcommand=kw_vsb.set)
        self._kw_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        kw_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._kw_tree.bind("<<TreeviewSelect>>", self._on_keyword_selected)
        self._kw_tree.bind("<Button-1>", self._on_keyword_click, add="+")

        # ── Right: Network Requests panel (DevTools style) ───────────
        net_outer = ttk.LabelFrame(paned, text="Network Requests", padding=0)
        paned.add(net_outer, weight=9)

        net_filter_row = ttk.Frame(net_outer)
        net_filter_row.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Label(net_filter_row, text="Filter:").pack(side=tk.LEFT)
        net_filter_entry = ttk.Entry(
            net_filter_row,
            textvariable=self._net_text_filter_var,
            width=22,
        )
        net_filter_entry.pack(side=tk.LEFT, padx=(6, 6), fill=tk.X, expand=True)
        net_filter_entry.bind("<KeyRelease>", self._on_net_filter_changed)
        ttk.Button(net_filter_row, text="Clear", command=self._clear_net_text_filter).pack(
            side=tk.LEFT
        )

        style = ttk.Style()
        style.configure(
            "Net.Treeview",
            background=_NET_BG,
            fieldbackground=_NET_BG,
            foreground=_NET_FG,
            rowheight=18,
            font=("Courier", 8),
        )
        style.configure("Net.Treeview.Heading",
                        background="#F1F3F4",
                        foreground="#5F6368",
                        font=("Helvetica", 8, "bold"))

        net_cols = ("name", "type", "status", "time")
        self._net_tree = ttk.Treeview(
            net_outer, columns=net_cols, show="headings",
            style="Net.Treeview", selectmode="browse",
        )
        self._net_tree.heading("name",   text="Name",   anchor=tk.W)
        self._net_tree.heading("type",   text="Type",   anchor=tk.CENTER)
        self._net_tree.heading("status", text="Status", anchor=tk.CENTER)
        self._net_tree.heading("time",   text="Time",   anchor=tk.CENTER)
        self._net_tree.column("name",   width=500, anchor=tk.W)
        self._net_tree.column("type",   width=64,  anchor=tk.CENTER, stretch=False)
        self._net_tree.column("status", width=56,  anchor=tk.CENTER, stretch=False)
        self._net_tree.column("time",   width=72,  anchor=tk.CENTER, stretch=False)

        self._net_tree.tag_configure("match",       background=_NET_BG_MATCH,
                                                    foreground=_NET_FG_MATCH)
        self._net_tree.tag_configure("no_match",    background=_NET_BG,
                                                    foreground=_NET_FG)
        self._net_tree.tag_configure("no_match_alt",background=_NET_BG_ALT,
                                                    foreground=_NET_FG)
        self._net_tree.tag_configure("err",         background=_NET_BG,
                                                    foreground="#D93025")
        self._net_tree.tag_configure("err_alt",     background=_NET_BG_ALT,
                                                    foreground="#D93025")

        net_vsb = ttk.Scrollbar(net_outer, orient="vertical",
                                command=self._net_tree.yview)
        self._net_tree.configure(yscrollcommand=net_vsb.set)
        self._net_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        net_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._net_tree.bind("<ButtonRelease-1>", self._on_net_row_clicked)
        self.root.after_idle(self._set_default_keyword_panel_width)
        self.root.after_idle(self._expand_keyword_panel_for_content)

    # ── Progress + Start ─────────────────────────────────────────────
    def _build_progress_bar(self) -> None:
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill=tk.X, padx=10, pady=5)

        self._progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(
            ctrl, variable=self._progress_var, maximum=100,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        self._start_btn = ttk.Button(
            ctrl, text="▶  Start", style="Accent.TButton",
            command=self._start,
        )
        self._start_btn.pack(side=tk.RIGHT)

    # ── DevTools-style Console Log ────────────────────────────────────
    def _build_log_panel(self) -> None:
        log_outer = ttk.LabelFrame(self.root, text="Console Log", padding=0)
        log_outer.pack(fill=tk.X, padx=10, pady=(0, 8))

        style = ttk.Style()
        style.configure(
            "Log.Treeview",
            background=_LOG_BG,
            fieldbackground=_LOG_BG,
            foreground=_LOG_FG["INFO"],
            rowheight=20,
            font=S.FONT_MONO,
        )
        style.configure("Log.Treeview.Heading",
                        background="#2D3748", foreground="#A0AEC0",
                        font=("Helvetica", 9, "bold"))

        log_cols = ("time", "level", "message")
        self._log_tree = ttk.Treeview(
            log_outer, columns=log_cols, show="headings",
            height=7, style="Log.Treeview", selectmode="browse",
        )
        self._log_tree.heading("time",    text="Time",    anchor=tk.W)
        self._log_tree.heading("level",   text="Level",   anchor=tk.CENTER)
        self._log_tree.heading("message", text="Message", anchor=tk.W)
        self._log_tree.column("time",    width=68,  anchor=tk.W,      stretch=False)
        self._log_tree.column("level",   width=64,  anchor=tk.CENTER, stretch=False)
        self._log_tree.column("message", width=950, anchor=tk.W)

        for level, fg in _LOG_FG.items():
            self._log_tree.tag_configure(level, background=_LOG_BG, foreground=fg)
        self._log_tree.tag_configure(
            "INFO_ALT", background=_LOG_ROW_ALT, foreground=_LOG_FG["INFO"]
        )

        log_vsb = ttk.Scrollbar(log_outer, orient="vertical",
                                command=self._log_tree.yview)
        self._log_tree.configure(yscrollcommand=log_vsb.set)
        self._log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # ================================================================
    # User actions
    # ================================================================

    def _load_excel(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Config Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            url_items, keyword_items = load_excel_to_models(path)
            self._excel_path    = path
            self._urls          = apply_style_to_url_items(url_items)
            self._keyword_items = keyword_items

            self._task_name_var.set(Path(path).stem)
            self._refresh_url_combo()
            self._refresh_keyword_tree()

            self._log(
                f"Loaded '{Path(path).name}': "
                f"{len(url_items)} URL(s), {len(keyword_items)} keyword(s)"
            )
            self._update_summary()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load Excel:\n{exc}",
                                 parent=self.root)

    def _open_url_manager(self) -> None:
        UrlManagerDialog(
            parent=self.root,
            current_urls=list(self._urls),
            on_save=self._on_urls_saved,
        )

    def _open_login_manager(self) -> None:
        LoginManagerDialog(
            parent=self.root,
            current_credentials=dict(self._login_credentials),
            on_save=self._on_login_saved,
        )

    def _on_login_saved(self, credentials: Dict[str, str]) -> None:
        self._login_credentials = {
            "username": credentials.get("username", "").strip(),
            "password": credentials.get("password", "").strip(),
        }
        save_login_credentials(self._login_credentials)
        self._log("Saved login credentials for authentication prompts")

    def _on_urls_saved(self, urls: List[UrlItem]) -> None:
        self._urls = urls
        self._refresh_url_combo()
        self._update_summary()

    def _start(self) -> None:
        if self._is_running:
            return
        if not self._urls:
            messagebox.showwarning("No URLs",
                                   "Please add at least one URL.",
                                   parent=self.root)
            return
        if not self._keyword_items:
            messagebox.showwarning("No Keywords",
                                   "Please load a keywords Excel file.",
                                   parent=self.root)
            return
        task_name = self._task_name_var.get().strip()
        if not task_name:
            messagebox.showwarning("No Task Name",
                                   "Please enter a task name.",
                                   parent=self.root)
            return
        try:
            self._workspace = create_workspace(task_name)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)
            return

        self._is_running = True
        self._start_btn.config(state=tk.DISABLED)
        self._progress_var.set(0)

        # Clear network panel before new run
        self.root.after(0, self._clear_network_panel)
        self._reset_keyword_statuses()

        self._log(f"Starting: {task_name}")
        self._log(f"Workspace: {self._workspace}")

        threading.Thread(target=self._run_automation, daemon=True).start()

    # ================================================================
    # Automation runner  (background thread)
    # ================================================================

    def _run_automation(self) -> None:
        automation = BrowserAutomation(
            keyword_items=self._keyword_items,
            login_username=self._login_credentials.get("username", ""),
            login_password=self._login_credentials.get("password", ""),
            on_status_change=self._cb_status_change,
            on_log=self._log,
            on_progress=self._cb_progress,
            on_request=self._cb_request,
            on_keyword_result=self._cb_keyword_result,
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            entries = loop.run_until_complete(
                automation.run(self._urls, str(self._workspace))
            )
        finally:
            loop.close()

        self.root.after(0, self._on_automation_done, entries)

    def _on_automation_done(self, entries: List[ReportEntry]) -> None:
        aligned_entries = align_entries_to_keywords(entries, self._keyword_items)
        ordered_entries = [entry for entry in aligned_entries if entry is not None]

        self._finalize_keyword_statuses(aligned_entries)
        self._generate_evidence_after_browser_closed(aligned_entries)

        task_name = self._task_name_var.get().strip() or "Task"
        report_path = str(build_report_output_path(task_name))
        try:
            if not self._excel_path:
                raise ValueError("Input Excel path is missing")
            saved = ReportWriter().write_into_input_copy(
                ordered_entries,
                input_excel_path=self._excel_path,
                output_path=report_path,
            )
            self._log(f"✅ Report saved → {saved}")
            messagebox.showinfo("Done", f"Report saved to:\n{saved}",
                                parent=self.root)
        except Exception as exc:
            self._log(f"💥 Report error: {exc}")
            messagebox.showerror("Report Error", str(exc), parent=self.root)

        self._is_running = False
        self._start_btn.config(state=tk.NORMAL)

    # ================================================================
    # Callbacks from BrowserAutomation  (thread-safe via root.after)
    # ================================================================

    def _cb_status_change(self, url_item: UrlItem, status: UrlStatus) -> None:
        url_item.status = status
        if status == UrlStatus.RUNNING:
            # Sync combobox to currently-running URL.
            self.root.after(0, self._select_url_in_combo, url_item.num)

    def _generate_evidence_after_browser_closed(
        self, aligned_entries: List[Optional[ReportEntry]]
    ) -> None:
        """
        Browser is already closed at this point.
        For each report row, select its keyword filter, capture GUI screenshot,
        then stitch GUI(left) + page snapshot(right) as final evidence.
        """
        if not self._workspace or not aligned_entries:
            return

        try:
            from PIL import ImageGrab
        except Exception:
            self._log("⚠️  ImageGrab unavailable; skip evidence screenshots")
            for entry in aligned_entries:
                if entry is not None:
                    entry.screenshot_path = None
            return

        if not is_screen_capture_allowed():
            request_screen_capture_access()
            if not is_screen_capture_allowed():
                self._log("⚠️  Screen Recording permission not active; skip GUI capture and keep page screenshots")
                messagebox.showwarning(
                    "Screen Recording Required",
                    "Please allow Screen Recording for this app, then quit and reopen the app.\n"
                    "If permission appears already enabled, run:\n"
                    "tccutil reset ScreenCapture",
                    parent=self.root,
                )
                return

        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
            try:
                self.root.focus_force()
            except Exception:
                pass
            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.25)

            for idx, entry in enumerate(aligned_entries, start=1):
                if entry is None:
                    continue
                self._select_url_in_combo(entry.url_index)
                self._select_keyword_filter_by_index(idx - 1)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(0.12)

                gui_shot = str(self._workspace / f"gui_{entry.url_index}_{idx}.png")
                gui_captured = False
                try:
                    x = self.root.winfo_rootx()
                    y = self.root.winfo_rooty()
                    w = self.root.winfo_width()
                    h = self.root.winfo_height()
                    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(gui_shot)
                    gui_captured = True
                except Exception as exc:
                    self._log(f"⚠️  GUI capture failed, use page screenshot fallback: {exc}")

                safe_text = re.sub(r"[^A-Za-z0-9._-]+", "_", entry.kw_text).strip("_")
                if not safe_text:
                    safe_text = "kw"
                stitched = str(
                    self._workspace
                    / f"evidence_{entry.url_index}_{entry.kw_lang}_{entry.kw_num}_{safe_text}_{idx}.png"
                )
                page_shot = entry.screenshot_path
                try:
                    if gui_captured and page_shot and os.path.exists(page_shot):
                        stitch_side_by_side(gui_shot, page_shot, stitched)
                        entry.screenshot_path = stitched
                    elif page_shot and os.path.exists(page_shot):
                        entry.screenshot_path = page_shot
                    else:
                        entry.screenshot_path = None
                finally:
                    if gui_captured:
                        try:
                            os.remove(gui_shot)
                        except Exception:
                            pass
        finally:
            try:
                self.root.attributes("-topmost", False)
            except Exception:
                pass

    def _finalize_keyword_statuses(
        self,
        aligned_entries: List[Optional[ReportEntry]],
    ) -> None:
        """
        Ensure every keyword row ends with PASS/FAILED after run completes.
        """
        for idx, iid in enumerate(self._kw_iid_list):
            try:
                entry = aligned_entries[idx] if idx < len(aligned_entries) else None
                tag = "PASS" if (entry and entry.result == "PASS") else "FAILED"
                vals = list(self._kw_tree.item(iid, "values"))
                vals[6] = tag
                self._kw_tree.item(iid, values=vals, tags=(tag,))
            except (tk.TclError, IndexError):
                pass

    def _select_keyword_filter_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._kw_iid_list):
            return
        iid = self._kw_iid_list[idx]
        self._kw_tree.selection_set(iid)
        self._kw_tree.focus(iid)
        self._ensure_keyword_row_visible_prefer_center(iid)
        self._on_keyword_selected()

    def _select_keyword_filter(self, num: int, lang: str, text: str) -> None:
        """
        Programmatically select a keyword row and trigger the existing filter flow.
        """
        for idx, kw in enumerate(self._keyword_items):
            if kw.num == num and kw.lang == lang and kw.text == text:
                if idx < len(self._kw_iid_list):
                    iid = self._kw_iid_list[idx]
                    self._kw_tree.selection_set(iid)
                    self._kw_tree.focus(iid)
                    self._kw_tree.see(iid)
                    self._on_keyword_selected()
                return

    def _cb_progress(self, done: int, total: int) -> None:
        pct = (done / total * 100) if total else 0
        self.root.after(0, self._progress_var.set, pct)

    def _cb_request(
        self,
        name: str,
        rtype: str,
        status: int,
        time_ms: int,
        matched: bool,
        matched_keys: List[Tuple[int, str, str]],
        source_num: int,
        source_lang: str,
        source_url: str,
    ) -> None:
        """Called for every completed network response in real time."""
        self.root.after(
            0,
            self._queue_network_row,
            name,
            rtype,
            status,
            time_ms,
            matched,
            matched_keys,
            source_num,
            source_lang,
            source_url,
        )

    def _queue_network_row(
        self,
        name: str,
        rtype: str,
        status: int,
        time_ms: int,
        matched: bool,
        matched_keys: List[Tuple[int, str, str]],
        source_num: int,
        source_lang: str,
        source_url: str,
    ) -> None:
        """
        Queue network rows and flush in small batches to reduce UI scheduling
        overhead under high request throughput.
        """
        self._pending_network_rows.append(
            (
                name,
                rtype,
                status,
                time_ms,
                matched,
                matched_keys,
                source_num,
                source_lang,
                source_url,
            )
        )
        if not self._net_flush_scheduled:
            self._net_flush_scheduled = True
            self.root.after(16, self._flush_network_rows)

    def _flush_network_rows(self) -> None:
        self._net_flush_scheduled = False
        while self._pending_network_rows:
            (
                name,
                rtype,
                status,
                time_ms,
                matched,
                matched_keys,
                source_num,
                source_lang,
                source_url,
            ) = self._pending_network_rows.popleft()
            self._append_network_row(
                name,
                rtype,
                status,
                time_ms,
                matched,
                matched_keys,
                source_num,
                source_lang,
                source_url,
            )

    def _cb_keyword_result(
        self,
        matched_keys: Set[Tuple[int, str, str]],
        current_num: int,
        current_lang: str,
    ) -> None:
        """Called after each URL finishes; updates per-keyword status."""
        self.root.after(
            0,
            self._update_keyword_statuses,
            matched_keys,
            current_num,
            current_lang,
        )

    # ================================================================
    # UI helpers
    # ================================================================

    def _refresh_url_combo(self) -> None:
        values = [f"[{u.num}][{u.lang}]  {u.url}" for u in self._urls]
        self._url_combo["values"] = values
        if values:
            self._url_combo.current(0)
        else:
            self._url_combo_var.set("")

    def _select_url_in_combo(self, num: int) -> None:
        idx = next((i for i, u in enumerate(self._urls) if u.num == num), None)
        if idx is not None:
            self._url_combo.current(idx)

    def _refresh_keyword_tree(self) -> None:
        self._kw_tree.delete(*self._kw_tree.get_children())
        self._kw_iid_list = []
        for kw in self._keyword_items:
            # lang shown as 2-letter code directly (tc/sc/en or "—" if blank)
            lang_label = kw.lang if kw.lang else "—"
            tag_label = kw.tag_type if kw.tag_type else "other"
            text1_label = kw.secondary_text if kw.secondary_text else "—"
            btn_label  = kw.button_name if kw.button_name else "—"
            iid = self._kw_tree.insert(
                "", tk.END,
                values=(kw.num if kw.num else "—", lang_label, tag_label,
                        text1_label, kw.text, btn_label, "STANDBY"),
                tags=("STANDBY",),
            )
            self._kw_iid_list.append(iid)
        self._autosize_keyword_columns()
        self.root.after_idle(self._expand_keyword_panel_for_content)

    def _autosize_keyword_columns(self) -> None:
        measure_font = tkfont.Font(font=("Courier", 8))
        minimum_widths = {
            "#": 30,
            "Lang": 36,
            "Tag": 48,
            "Text1": 96,
            "Text2": 96,
            "Button": 90,
            "Status": 60,
        }
        total = 0
        for col in self._kw_cols:
            heading = self._kw_tree.heading(col, option="text")
            max_px = measure_font.measure(str(heading)) + 18
            for iid in self._kw_tree.get_children():
                value = self._kw_tree.set(iid, col)
                max_px = max(max_px, measure_font.measure(str(value)) + 18)
            width = max(max_px, minimum_widths.get(col, 80))
            self._kw_tree.column(col, width=width)
            total += width
        self._kw_content_width = total

    def _expand_keyword_panel_for_content(self) -> None:
        if not hasattr(self, "_center_paned") or not hasattr(self, "_kw_frame"):
            return
        content_width = getattr(self, "_kw_content_width", 0)
        if content_width <= 0:
            return
        self.root.update_idletasks()
        root_width = max(self.root.winfo_width(), 1000)
        max_left = max(420, root_width - 420)
        target = min(content_width + 28, max_left)
        try:
            self._center_paned.paneconfigure(self._kw_frame, minsize=target)
            current = self._center_paned.sashpos(0)
            if current < target:
                self._center_paned.sashpos(0, target)
        except tk.TclError:
            pass

    def _set_default_keyword_panel_width(self) -> None:
        if not hasattr(self, "_center_paned"):
            return
        self.root.update_idletasks()
        root_width = max(self.root.winfo_width(), 1000)
        target = int(root_width * 0.55)
        try:
            self._center_paned.sashpos(0, target)
        except tk.TclError:
            pass

    def _reset_keyword_statuses(self) -> None:
        for iid in self._kw_iid_list:
            try:
                vals = list(self._kw_tree.item(iid, "values"))
                vals[6] = "STANDBY"
                self._kw_tree.item(iid, values=vals, tags=("STANDBY",))
            except tk.TclError:
                pass

    def _update_keyword_statuses(
        self,
        matched_keys: Set[Tuple[int, str, str]],
        current_num: int,
        current_lang: str,
    ) -> None:
        for idx, iid in enumerate(self._kw_iid_list):
            try:
                kw   = self._keyword_items[idx]
                # Only evaluate rows that belong to the current page num/lang.
                if kw.num != current_num or kw.lang != current_lang:
                    continue
                key  = (kw.num, kw.lang, kw.text)
                tag  = "PASS" if key in matched_keys else "FAILED"
                vals = list(self._kw_tree.item(iid, "values"))
                vals[6] = tag
                self._kw_tree.item(iid, values=vals, tags=(tag,))
            except (tk.TclError, IndexError):
                pass

    def _clear_network_panel(self) -> None:
        self._net_tree.delete(*self._net_tree.get_children())
        self._net_row_count = 0
        self._all_network_events = []
        self._displayed_network_events = {}
        self._current_filter = None
        self._net_text_filter_var.set("")
        self._pending_network_rows.clear()
        self._net_flush_scheduled = False

    def _append_network_row(
        self,
        name: str,
        rtype: str,
        status: int,
        time_ms: int,
        matched: bool,
        matched_keys: List[Tuple[int, str, str]],
        source_num: int,
        source_lang: str,
        source_url: str,
    ) -> None:
        event = NetworkEvent(
            name=name,
            rtype=rtype,
            status=status,
            time_ms=time_ms,
            matched=matched,
            matched_keywords={
                KeywordIdentity(num=n, lang=l, name=t) for n, l, t in matched_keys
            },
            source_num=source_num,
            source_lang=source_lang,
            source_url=source_url,
        )
        self._all_network_events.append(event)
        if self._event_matches_filters(event):
            self._insert_network_event(event)

    def _insert_network_event(self, event: NetworkEvent) -> None:
        self._net_row_count += 1
        is_error = event.status >= 400
        time_str = f"{event.time_ms} ms"

        if event.matched:
            tag = "match"
        elif is_error:
            tag = "err" if self._net_row_count % 2 != 0 else "err_alt"
        elif self._net_row_count % 2 == 0:
            tag = "no_match_alt"
        else:
            tag = "no_match"

        iid = self._net_tree.insert(
            "",
            tk.END,
            values=(self._ellipsize(event.name), event.rtype, event.status, time_str),
            tags=(tag,),
        )
        self._displayed_network_events[iid] = event
        self._net_tree.see(iid)

    def _render_network_events(self, events: List[NetworkEvent]) -> None:
        self._net_tree.delete(*self._net_tree.get_children())
        self._net_row_count = 0
        self._displayed_network_events = {}
        for ev in events:
            if self._event_matches_filters(ev):
                self._insert_network_event(ev)

    def _on_keyword_selected(self, _event=None) -> None:
        selection = self._kw_tree.selection()
        if not selection:
            self._current_filter = None
            self._render_network_events(self._all_network_events)
            return

        iid = selection[0]
        if iid not in self._kw_iid_list:
            self._current_filter = None
            self._render_network_events(self._all_network_events)
            return

        idx = self._kw_iid_list.index(iid)
        if idx >= len(self._keyword_items):
            self._current_filter = None
            self._render_network_events(self._all_network_events)
            return

        kw = self._keyword_items[idx]
        self._current_filter = KeywordIdentity(num=kw.num, lang=kw.lang, name=kw.text)
        trigger_keyword_filter(
            self._all_network_events,
            num=kw.num,
            lang=kw.lang,
            name=kw.text,
            on_filtered=self._render_network_events,
        )

    def _on_keyword_click(self, event) -> Optional[str]:
        row_id = self._kw_tree.identify_row(event.y)
        if not row_id:
            return None
        selected = self._kw_tree.selection()
        if selected and selected[0] == row_id:
            self._clear_keyword_filter()
            return "break"
        return None

    def _clear_keyword_filter(self) -> None:
        self._kw_tree.selection_remove(self._kw_tree.selection())
        self._current_filter = None
        self._render_network_events(self._all_network_events)

    def _on_net_filter_changed(self, _event=None) -> None:
        self._render_network_events(self._all_network_events)

    def _clear_net_text_filter(self) -> None:
        self._net_text_filter_var.set("")
        self._render_network_events(self._all_network_events)

    def _event_matches_filters(self, event: NetworkEvent) -> bool:
        if self._current_filter is not None:
            if self._current_filter not in event.matched_keywords:
                return False
            # Limit logs to the same sequence/page context (num + lang).
            if (
                event.source_num != self._current_filter.num
                or event.source_lang != self._current_filter.lang
            ):
                return False
        query = self._net_text_filter_var.get().strip().lower()
        if query and query not in event.name.lower():
            return False
        return True

    def _ensure_keyword_row_visible_prefer_center(self, iid: str) -> None:
        children = list(self._kw_tree.get_children())
        if not children or iid not in children:
            return
        idx = children.index(iid)
        total = len(children)
        if total <= 1:
            self._kw_tree.see(iid)
            return

        self._kw_tree.update_idletasks()
        row_height = 18
        try:
            bbox = self._kw_tree.bbox(children[0])
            if bbox and len(bbox) >= 4 and bbox[3] > 0:
                row_height = bbox[3]
        except tk.TclError:
            pass
        widget_height = max(self._kw_tree.winfo_height(), row_height * 3)
        visible_rows = max(1, widget_height // max(1, row_height))

        if idx <= visible_rows // 2:
            self._kw_tree.yview_moveto(0.0)
            self._kw_tree.see(iid)
            return
        if idx >= total - (visible_rows // 2) - 1:
            self._kw_tree.yview_moveto(1.0)
            self._kw_tree.see(iid)
            return

        top_index = max(0, idx - visible_rows // 2)
        max_top = max(1, total - visible_rows)
        fraction = min(1.0, max(0.0, top_index / max_top))
        self._kw_tree.yview_moveto(fraction)
        self._kw_tree.see(iid)

    def _on_net_row_clicked(self, event) -> None:
        row_id = self._net_tree.identify_row(event.y)
        if not row_id:
            return
        item = self._displayed_network_events.get(row_id)
        if not item:
            return
        messagebox.showinfo("Log Detail", item.name, parent=self.root)

    def _ellipsize(self, text: str, max_len: int = 90) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    def _update_summary(self) -> None:
        self._summary_var.set(
            f"URLs: {len(self._urls)}  |  Keywords: {len(self._keyword_items)}"
        )

    def _log(self, message: str) -> None:
        def _do() -> None:
            ts    = datetime.now().strftime("%H:%M:%S")
            level = _detect_level(message)
            tag   = level
            if level == "INFO":
                tag = "INFO" if self._log_row_count % 2 == 0 else "INFO_ALT"
            iid = self._log_tree.insert(
                "", tk.END,
                values=(ts, level, message),
                tags=(tag,),
            )
            self._log_row_count += 1
            self._log_tree.see(iid)
        self.root.after(0, _do)
