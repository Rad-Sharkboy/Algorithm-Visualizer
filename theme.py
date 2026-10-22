"""Light/dark palettes, native font choices, and live Tk recoloring."""

from dataclasses import dataclass
import sys
import tkinter as tk
from tkinter import font as tkfont


@dataclass(frozen=True)
class Palette:
    BG: str
    SIDEBAR: str
    PANEL: str
    INSET: str
    BORDER: str
    TEXT: str
    MUTED: str
    ACCENT: str
    PURPLE: str
    GOLD: str
    GREEN: str
    RED: str
    SELECT: str
    SELECT_BORDER: str
    HOVER: str
    GRID: str
    AXIS: str
    DISCARDED: str
    TOOLTIP_BORDER: str
    ON_ACCENT: str
    GLASS_TOP: str
    GLASS_BOTTOM: str
    SHINE: str


PALETTES = {
    "Dark": Palette(
        BG="#0a101c", SIDEBAR="#0e1625", PANEL="#111d2e", INSET="#0c1524",
        BORDER="#29394e", TEXT="#edf3fc", MUTED="#a0afc4", ACCENT="#65e5c4",
        PURPLE="#b5a1ff", GOLD="#f5c773", GREEN="#70e5a0", RED="#ff8b9e",
        SELECT="#18372f", SELECT_BORDER="#32685b", HOVER="#1d3044",
        GRID="#243248", AXIS="#8193ae", DISCARDED="#4a5c75",
        TOOLTIP_BORDER="#607894", ON_ACCENT="#09291f", GLASS_TOP="#234d52",
        GLASS_BOTTOM="#163239", SHINE="#f4fffd",
    ),
    "Light": Palette(
        BG="#edf2f8", SIDEBAR="#e5ecf5", PANEL="#ffffff", INSET="#f1f5fa",
        BORDER="#c8d3e1", TEXT="#18273c", MUTED="#53647b", ACCENT="#087767",
        PURPLE="#7551c9", GOLD="#966100", GREEN="#167341", RED="#b83250",
        SELECT="#d4eee5", SELECT_BORDER="#83b8a8", HOVER="#d9e4f0",
        GRID="#e0e7f0", AXIS="#65768e", DISCARDED="#97a6ba",
        TOOLTIP_BORDER="#92a6bf", ON_ACCENT="#fafffd", GLASS_TOP="#fcfffe",
        GLASS_BOTTOM="#cbe7e2", SHINE="#f9fffe",
    ),
}


def system_theme():
    """Follow Windows' app preference, not its separate taskbar preference.

    Registry access is read-only. Missing keys, restricted access, and other
    operating systems use Dark; the manual Light/Dark choices always work.
    """
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "Light" if light else "Dark"
        except (ImportError, OSError):
            pass
    return "Dark"


def configure_fonts(root):
    """Prefer the host's UI and coding fonts; never download or bundle a font."""
    families = {name.casefold(): name for name in tkfont.families(root)}

    def choose(candidates, fallback):
        return next((families[name.casefold()] for name in candidates
                     if name.casefold() in families),
                    tkfont.nametofont(fallback, root=root).actual("family"))

    font = choose(("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue",
                   "Noto Sans", "DejaVu Sans", "Liberation Sans"), "TkDefaultFont")
    mono = choose(("Cascadia Code", "Cascadia Mono", "Consolas", "SF Mono", "Menlo",
                   "DejaVu Sans Mono", "Liberation Mono"), "TkFixedFont")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
                 "TkCaptionFont", "TkSmallCaptionFont"):
        tkfont.nametofont(name, root=root).configure(family=font)
    tkfont.nametofont("TkFixedFont", root=root).configure(family=mono)
    return font, mono


class StudioTheme:
    def __init__(self, root, mode="System"):
        self.root = root
        self.mode = mode
        self.name = system_theme() if mode == "System" else mode
        self.palette = PALETTES[self.name]
        self.font, self.mono = configure_fonts(root)

    def select(self, mode):
        if mode not in ("System", "Light", "Dark"):
            raise ValueError(f"Unknown appearance: {mode}")
        self.mode = mode
        name = system_theme() if mode == "System" else mode
        if name == self.name:
            return False
        previous = self.palette
        self.name, self.palette = name, PALETTES[name]
        colors = {value: getattr(self.palette, role) for role, value in vars(previous).items()}
        # Recolor existing widgets instead of rebuilding them: focus, selection,
        # open guides, algorithm iterators, and scheduled playback all survive.
        self._recolor(self.root, colors)
        return True

    def _recolor(self, widget, colors):
        options = widget.keys()
        changes = {}
        for option in ("background", "foreground", "activebackground", "activeforeground",
                       "disabledbackground", "disabledforeground", "highlightbackground",
                       "highlightcolor", "insertbackground", "selectbackground",
                       "selectforeground", "selectcolor", "readonlybackground"):
            if option in options:
                current = str(widget.cget(option)).lower()
                if current in colors:
                    changes[option] = colors[current]
        if changes:
            widget.configure(**changes)
        if hasattr(widget, "refresh_theme"):
            widget.refresh_theme()
        elif isinstance(widget, tk.Canvas):
            for item in widget.find_all():
                for option in ("fill", "outline"):
                    if option in widget.itemconfigure(item):
                        current = widget.itemcget(item, option).lower()
                        if current in colors:
                            widget.itemconfigure(item, **{option: colors[current]})
        for child in widget.winfo_children():
            self._recolor(child, colors)

    def label(self, parent, text="", size=10, color=None, bold=False, bg=None, **kwargs):
        return tk.Label(parent, text=text, bg=bg or parent.cget("bg"),
                        fg=color or self.palette.TEXT,
                        font=(self.font, size, "bold" if bold else "normal"), **kwargs)

    def button(self, parent, text, command, primary=False, width=None):
        p = self.palette
        return tk.Button(parent, text=text, command=command,
                         bg=p.ACCENT if primary else p.BORDER,
                         fg=p.ON_ACCENT if primary else p.TEXT,
                         activebackground=p.SELECT if primary else p.HOVER,
                         activeforeground=p.TEXT, disabledforeground=p.MUTED,
                         relief="flat", bd=0, padx=14, pady=9, cursor="hand2", width=width,
                         font=(self.font, 10, "bold"), highlightthickness=1,
                         highlightbackground=p.ACCENT if primary else p.BORDER,
                         highlightcolor=p.ACCENT, takefocus=True)
