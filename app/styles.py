"""
Centralised colour palette, font definitions, and ttk style configuration.
Import this module; never hard-code colours/fonts in widget code.
"""
from tkinter import ttk

# ── Palette ─────────────────────────────────────────────────────────
COLOR_BG          = "#F0F4F8"
COLOR_ACCENT      = "#4299E1"
COLOR_ACCENT_DARK = "#2B6CB0"
COLOR_PASS        = "#9AE6B4"
COLOR_FAILED      = "#FEB2B2"
COLOR_RUNNING     = "#FAF089"
COLOR_STANDBY     = "#E2E8F0"
COLOR_WHITE       = "#FFFFFF"
COLOR_TEXT        = "#2D3748"
COLOR_TEXT_LIGHT  = "#718096"
COLOR_CONSOLE_BG  = "#1A202C"
COLOR_CONSOLE_FG  = "#A0AEC0"
COLOR_HEADING_BG  = "#2D3748"   # dark heading background (shared by log & kw panels)
COLOR_HEADING_FG  = "#A0AEC0"   # heading foreground

# ── Fonts ────────────────────────────────────────────────────────────
FONT_TITLE  = ("Helvetica", 12, "bold")
FONT_BODY   = ("Helvetica", 10)
FONT_SMALL  = ("Helvetica", 8)
FONT_MONO   = ("Courier", 9)

# ── Status tag → background colour ───────────────────────────────────
STATUS_COLORS: dict = {
    "STANDBY": COLOR_STANDBY,
    "RUNNING": COLOR_RUNNING,
    "PASS":    COLOR_PASS,
    "FAILED":  COLOR_FAILED,
}


def configure_styles(style: ttk.Style) -> None:
    """Apply the application theme to a ttk.Style instance."""
    style.theme_use("clam")

    style.configure("TFrame",      background=COLOR_BG)
    style.configure("TLabelframe", background=COLOR_BG)
    style.configure("TLabelframe.Label", background=COLOR_BG,
                    foreground=COLOR_TEXT, font=FONT_BODY)
    style.configure("TLabel",      background=COLOR_BG,
                    foreground=COLOR_TEXT, font=FONT_BODY)
    style.configure("TEntry",      fieldbackground=COLOR_WHITE, font=FONT_BODY)

    style.configure(
        "TButton",
        font=FONT_BODY, padding=4,
        background=COLOR_ACCENT, foreground=COLOR_WHITE,
    )
    style.map("TButton", background=[("active", COLOR_ACCENT_DARK)])

    style.configure(
        "Accent.TButton",
        font=("Helvetica", 10, "bold"), padding=5,
        background=COLOR_ACCENT, foreground=COLOR_WHITE,
    )
    style.map("Accent.TButton", background=[("active", COLOR_ACCENT_DARK)])

    style.configure(
        "Treeview",
        rowheight=22, font=FONT_BODY,
        fieldbackground=COLOR_WHITE, background=COLOR_WHITE,
    )
    style.configure("Treeview.Heading",
                    font=("Helvetica", 9, "bold"))
    style.map("Treeview", background=[("selected", COLOR_ACCENT)])

    style.configure("TProgressbar",
                    troughcolor=COLOR_BG, background=COLOR_ACCENT)
    style.configure("TCombobox",   font=FONT_BODY)
