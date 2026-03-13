"""
URLManagerDialog — modal Toplevel for managing the URL list.

This dialog now focuses on URL style management:
    • Select URL title and language segment styles for pws/cms
    • Add/delete style options (persisted globally across tasks)
    • Rebuild and preview all URLs in real time
    • Confirm with Save to apply rebuilt URLs to current task
"""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import copy
from typing import Callable, Dict, List, Optional, Tuple

import app.styles as S
from models.config import LANG_MAP_INV
from models.session import UrlItem
from utils.url_style_options import (
    DEFAULT_URL_STYLE_OPTIONS,
        apply_style_to_url_items,
        load_url_style_options,
        save_url_style_options,
)


class UrlManagerDialog(tk.Toplevel):
    """
        Modal dialog for URL style management + URL preview.
    """

    def __init__(
        self,
        parent: tk.Widget,
        current_urls: List[UrlItem],
        on_save: Callable[[List[UrlItem]], None],
    ) -> None:
        super().__init__(parent)
        self.title("URL Manager")
        self.geometry("980x620")
        self.resizable(True, True)
        self.configure(bg=S.COLOR_BG)
        self.grab_set()          # modal

        self._on_save = on_save
        self._source_items: List[UrlItem] = [
            UrlItem(
                url=u.url,
                lang=u.lang,
                num=u.num,
                status=u.status,
                url_path=u.url_path,
                url_kind=u.url_kind,
            )
            for u in current_urls
        ]
        self._preview_items: List[UrlItem] = []

        self._style_options = load_url_style_options()
        self._selector_vars: Dict[Tuple[str, str, Optional[str]], tk.StringVar] = {}
        self._selector_boxes: Dict[Tuple[str, str, Optional[str]], ttk.Combobox] = {}

        self._build_ui()
        self._apply_style_and_refresh()

    # ================================================================
    # UI construction
    # ================================================================

    def _build_ui(self) -> None:
        # ── Global style options ────────────────────────────────────
        options_outer = ttk.LabelFrame(self, text="Global URL Style Options")
        options_outer.pack(fill=tk.X, padx=12, pady=(12, 8))

        self._build_kind_section(options_outer, kind="pws", title="PWS Style")
        self._build_kind_section(options_outer, kind="cms", title="CMS Style")

        # ── URL preview tree ────────────────────────────────────────
        tree_outer = ttk.LabelFrame(self, text="URL Preview (Real-time)")
        tree_outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        cols = ("#", "Type", "URL", "Language")
        self._tree = ttk.Treeview(
            tree_outer, columns=cols, show="headings", selectmode="browse"
        )
        self._tree.heading("#",        text="#",        anchor=tk.CENTER)
        self._tree.heading("Type",     text="Type",     anchor=tk.CENTER)
        self._tree.heading("URL",      text="URL",      anchor=tk.W)
        self._tree.heading("Language", text="Language", anchor=tk.CENTER)
        self._tree.column("#",        width=46,  anchor=tk.CENTER, stretch=False)
        self._tree.column("Type",     width=66,  anchor=tk.CENTER, stretch=False)
        self._tree.column("URL",      width=700, anchor=tk.W)
        self._tree.column("Language", width=140, anchor=tk.CENTER, stretch=False)

        vsb = ttk.Scrollbar(tree_outer, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Action buttons ───────────────────────────────────────────
        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, padx=12, pady=(4, 12))

        ttk.Button(
            btn_row,
            text="Restore Defaults",
            command=self._restore_defaults,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Cancel",
                   command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_row, text="Save", style="Accent.TButton",
                   command=self._save).pack(side=tk.RIGHT, padx=4)

    def _build_kind_section(self, parent: tk.Widget, kind: str, title: str) -> None:
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill=tk.X, padx=8, pady=6)

        self._build_selector_row(frame, label="Title", kind=kind, field="title")
        self._build_selector_row(frame, label="TC Language", kind=kind, field="lang", lang="tc")
        self._build_selector_row(frame, label="SC Language", kind=kind, field="lang", lang="sc")
        self._build_selector_row(frame, label="EN Language", kind=kind, field="lang", lang="en")

    def _build_selector_row(
        self,
        parent: tk.Widget,
        label: str,
        kind: str,
        field: str,
        lang: Optional[str] = None,
    ) -> None:
        key = (kind, field, lang)
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(row, text=f"{label}:", width=14).pack(side=tk.LEFT)

        var = tk.StringVar(value=self._get_selected_value(key))
        self._selector_vars[key] = var

        combo = ttk.Combobox(
            row,
            textvariable=var,
            values=self._get_option_values(key),
            width=40,
            state="readonly",
        )
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        combo.bind("<<ComboboxSelected>>", lambda _e, k=key: self._on_selector_changed(k))
        self._selector_boxes[key] = combo

        ttk.Button(row, text="Add", command=lambda k=key: self._add_option_value(k)).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(row, text="Delete", command=lambda k=key: self._delete_option_value(k)).pack(
            side=tk.LEFT
        )

    # ================================================================
    # Event handlers
    # ================================================================

    def _refresh_tree(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for item in self._preview_items:
            lang_label = LANG_MAP_INV.get(item.lang, item.lang)
            self._tree.insert(
                "",
                tk.END,
                values=(item.num, item.url_kind, item.url, lang_label),
            )

    def _save(self) -> None:
        self._on_save(list(self._preview_items))
        self.destroy()

    # ================================================================
    # Helpers
    # ================================================================

    def _apply_style_and_refresh(self) -> None:
        self._preview_items = apply_style_to_url_items(
            self._source_items,
            options=self._style_options,
        )
        self._refresh_tree()

    def _on_selector_changed(self, key: Tuple[str, str, Optional[str]]) -> None:
        selected = self._selector_vars[key].get().strip()
        options = self._get_option_values(key)
        if selected not in options:
            return
        self._set_selected_value(key, selected)
        self._persist_options()
        self._apply_style_and_refresh()

    def _add_option_value(self, key: Tuple[str, str, Optional[str]]) -> None:
        value = simpledialog.askstring("Add Option", "Enter new option value:", parent=self)
        if value is None:
            return
        new_value = value.strip()
        if not new_value:
            messagebox.showwarning("Empty", "Option value cannot be empty.", parent=self)
            return
        options = self._get_option_values(key)
        if new_value in options:
            messagebox.showinfo("Duplicate", "Option already exists.", parent=self)
            return
        options.append(new_value)
        self._set_option_values(key, options)
        self._set_selected_value(key, new_value)
        self._selector_vars[key].set(new_value)
        self._refresh_selector(key)
        self._persist_options()
        self._apply_style_and_refresh()

    def _delete_option_value(self, key: Tuple[str, str, Optional[str]]) -> None:
        current = self._selector_vars[key].get().strip()
        options = self._get_option_values(key)
        if current not in options:
            return
        if len(options) <= 1:
            messagebox.showwarning("Blocked", "At least one option must remain.", parent=self)
            return
        if not messagebox.askyesno(
            "Delete Option",
            f"Delete option '{current}'?",
            parent=self,
        ):
            return
        options = [item for item in options if item != current]
        self._set_option_values(key, options)
        fallback = options[0]
        self._set_selected_value(key, fallback)
        self._selector_vars[key].set(fallback)
        self._refresh_selector(key)
        self._persist_options()
        self._apply_style_and_refresh()

    def _refresh_selector(self, key: Tuple[str, str, Optional[str]]) -> None:
        combo = self._selector_boxes[key]
        combo["values"] = self._get_option_values(key)

    def _persist_options(self) -> None:
        save_url_style_options(self._style_options)

    def _restore_defaults(self) -> None:
        if not messagebox.askyesno(
            "Restore Defaults",
            "Restore all URL style options to defaults?",
            parent=self,
        ):
            return
        self._style_options = copy.deepcopy(DEFAULT_URL_STYLE_OPTIONS)
        self._refresh_all_selectors()
        self._persist_options()
        self._apply_style_and_refresh()

    def _refresh_all_selectors(self) -> None:
        for key, var in self._selector_vars.items():
            var.set(self._get_selected_value(key))
            self._refresh_selector(key)

    def _get_option_values(self, key: Tuple[str, str, Optional[str]]) -> List[str]:
        kind, field, lang = key
        if field == "title":
            return list(self._style_options["titles"][kind])
        return list(self._style_options["langs"][kind][lang])

    def _set_option_values(self, key: Tuple[str, str, Optional[str]], values: List[str]) -> None:
        kind, field, lang = key
        if field == "title":
            self._style_options["titles"][kind] = list(values)
            return
        self._style_options["langs"][kind][lang] = list(values)

    def _get_selected_value(self, key: Tuple[str, str, Optional[str]]) -> str:
        kind, field, lang = key
        if field == "title":
            return self._style_options["selected"]["titles"][kind]
        return self._style_options["selected"]["langs"][kind][lang]

    def _set_selected_value(self, key: Tuple[str, str, Optional[str]], value: str) -> None:
        kind, field, lang = key
        if field == "title":
            self._style_options["selected"]["titles"][kind] = value
            return
        self._style_options["selected"]["langs"][kind][lang] = value
