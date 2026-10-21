"""Shared colors, font fallbacks, and widget styling for Algo Studio."""

import tkinter as tk
from tkinter import font as tkfont

BG = "#0a101c"
SIDEBAR = "#0e1625"
PANEL = "#111d2e"
INSET = "#0c1524"
BORDER = "#243147"
TEXT = "#edf3fc"
MUTED = "#8b9bb4"
ACCENT = "#56e0bf"
PURPLE = "#b09aff"
GOLD = "#f5c773"
GREEN = "#70e5a0"
RED = "#ff8b9e"
FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"


def label(parent, text="", size=10, color=TEXT, bold=False, bg=None, **kwargs):
    return tk.Label(parent, text=text, bg=bg or parent.cget("bg"), fg=color,
                    font=(FONT, size, "bold" if bold else "normal"), **kwargs)


def button(parent, text, command, primary=False, width=None):
    return tk.Button(parent, text=text, command=command,
                     bg=ACCENT if primary else BORDER, fg=BG if primary else TEXT,
                     activebackground="#8befd5" if primary else "#33435d",
                     activeforeground=BG if primary else TEXT,
                     disabledforeground="#62718b", relief="flat", bd=0,
                     padx=14, pady=9, cursor="hand2", width=width,
                     font=(FONT, 10, "bold"), highlightthickness=1,
                     highlightbackground=ACCENT if primary else BORDER,
                     highlightcolor=TEXT, takefocus=True)


def configure_fonts(root):
    global FONT, MONO
    families = {name.casefold() for name in tkfont.families(root)}
    FONT = next((name for name in ("DejaVu Sans", "Segoe UI", "Helvetica")
                 if name.casefold() in families), "TkDefaultFont")
    MONO = next((name for name in ("DejaVu Sans Mono", "Consolas", "Courier")
                 if name.casefold() in families), "TkFixedFont")
    tkfont.nametofont("TkDefaultFont", root=root).configure(family=FONT, size=10)
    return FONT, MONO
