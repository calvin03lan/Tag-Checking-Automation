"""
LoginManagerDialog — modal dialog for editing authentication credentials.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict

import app.styles as S
from utils.login_credentials import DEFAULT_LOGIN_CREDENTIALS


class LoginManagerDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        current_credentials: Dict[str, str],
        on_save: Callable[[Dict[str, str]], None],
    ) -> None:
        super().__init__(parent)
        self.title("Login Management")
        self.geometry("520x220")
        self.resizable(False, False)
        self.configure(bg=S.COLOR_BG)
        self.grab_set()

        self._on_save = on_save
        self._username_var = tk.StringVar(value=current_credentials.get("username", ""))
        self._password_var = tk.StringVar(value=current_credentials.get("password", ""))
        self._show_password_var = tk.BooleanVar(value=False)
        self._password_entry: ttk.Entry | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.LabelFrame(self, text="Credentials", padding=12)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        ttk.Label(frame, text="Login ID:").grid(row=0, column=0, sticky=tk.W, pady=(4, 8))
        ttk.Entry(frame, textvariable=self._username_var, width=44).grid(
            row=0, column=1, sticky=tk.EW, pady=(4, 8)
        )

        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=(0, 8))
        self._password_entry = ttk.Entry(frame, textvariable=self._password_var, width=44, show="*")
        self._password_entry.grid(
            row=1, column=1, sticky=tk.EW, pady=(0, 8)
        )
        ttk.Checkbutton(
            frame,
            text="Show Password",
            variable=self._show_password_var,
            command=self._toggle_password_visibility,
        ).grid(row=2, column=1, sticky=tk.W, pady=(0, 4))

        frame.grid_columnconfigure(1, weight=1)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(row, text="Restore Default", command=self._restore_default).pack(side=tk.LEFT)
        ttk.Button(row, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(row, text="Save", style="Accent.TButton", command=self._save).pack(
            side=tk.RIGHT, padx=4
        )

    def _restore_default(self) -> None:
        self._username_var.set(DEFAULT_LOGIN_CREDENTIALS["username"])
        self._password_var.set(DEFAULT_LOGIN_CREDENTIALS["password"])

    def _toggle_password_visibility(self) -> None:
        if self._password_entry is None:
            return
        self._password_entry.configure(show="" if self._show_password_var.get() else "*")

    def _save(self) -> None:
        username = self._username_var.get().strip()
        password = self._password_var.get().strip()
        if not username or not password:
            messagebox.showwarning("Invalid Credentials", "Login ID and Password are required.", parent=self)
            return
        self._on_save({"username": username, "password": password})
        self.destroy()
