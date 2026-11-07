"""Instrument palettes, type, spacing, and semantic widget color bindings."""

from types import SimpleNamespace
import sys
from tkinter import font as tkfont
import weakref

from motion import lerp_color, ease_in_out_quad
from layout import LayoutFrame, LayoutLabel, display_metrics
from aa_gfx import SpriteCache


THEMES = {
    "Dark": dict(BG="#0E0D0B", PANEL="#171512", INSET="#12110E", BORDER="#2A261F",
                 TEXT="#EDE6D6", MUTED="#8C8472", BAR="#FFB454", ACCENT="#FFB454",
                 COMPARE="#FF5A4E", PIVOT="#5CE1E6", SETTLED="#B6E36B",
                 DISCARDED="#554E41", ON_ACCENT="#0E0D0B"),
    "Light": dict(BG="#F2EDE2", PANEL="#FBF8F1", INSET="#EAE4D8", BORDER="#D8D0BE",
                  TEXT="#1C1A16", MUTED="#6D6553", BAR="#1F3A33", ACCENT="#92500F",
                  COMPARE="#B93428", PIVOT="#087A80", SETTLED="#526F1D",
                  DISCARDED="#A69D89", ON_ACCENT="#FBF8F1", THUMB="#FBF8F1"),
    "Red": dict(BG="#130D10", PANEL="#1D1418", INSET="#170F13", BORDER="#3B272F",
                TEXT="#F3E5E3", MUTED="#A68D94", BAR="#FA727A", ACCENT="#F27880",
                BAR_MID="#D93650", BAR_BASE="#771D39", BUTTON_TOP="#F58189", BUTTON_BASE="#E66379",
                COMPARE="#FFB7AB", PIVOT="#CCB7EF", SETTLED="#B8D59D",
                DISCARDED="#60434D", ON_ACCENT="#210F17"),
    "Maroon": dict(BG="#130C11", PANEL="#1E141C", INSET="#180F16", BORDER="#3B2835",
                   TEXT="#F0E3EB", MUTED="#AA8D9F", BAR="#E49ABA", ACCENT="#DF96B3",
                   BAR_MID="#AC487D", BAR_BASE="#551A3F", BUTTON_TOP="#E6A1BD", BUTTON_BASE="#D385A8",
                   COMPARE="#FF8B80", PIVOT="#CDBBEA", SETTLED="#C1D59E",
                   DISCARDED="#614454", ON_ACCENT="#210F1B"),
    "Purple": dict(BG="#110E15", PANEL="#1A1521", INSET="#15111B", BORDER="#382E43",
                   TEXT="#F0E8F2", MUTED="#A393B0", BAR="#CBA6DE", ACCENT="#C4A1D7",
                   BAR_MID="#9764B2", BAR_BASE="#4F2D65", BUTTON_TOP="#D0ADDF", BUTTON_BASE="#B691CD",
                   COMPARE="#FF9C9C", PIVOT="#F1BED5", SETTLED="#BFD7A4",
                   DISCARDED="#54425F", ON_ACCENT="#1B1024"),
}
for _palette in THEMES.values():
    for _role in ("BAR", "COMPARE", "PIVOT", "SETTLED", "DISCARDED"):
        _palette.setdefault(_role + "_MID", lerp_color(_palette["INSET"], _palette[_role], .8175))
        _palette.setdefault(_role + "_BASE", lerp_color(_palette["INSET"], _palette[_role], .695))
    _palette.setdefault("BUTTON_TOP", _palette["ACCENT"])
    _palette.setdefault("BUTTON_BASE", _palette["ACCENT"])
    _palette.setdefault("THUMB", _palette["TEXT"])

THEME_LABELS = {"System": "System", "Dark": "Phosphor", "Light": "Paper",
                "Red": "Red", "Maroon": "Maroon", "Purple": "Purple"}
FONT_FAMILIES = {
    "display": ("Georgia", "Cambria", "Palatino Linotype", "Palatino", "Liberation Serif", "DejaVu Serif"),
    "mono": ("Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Courier New"),
}
SPACING = dict(sidebar=210, outer=28, section=18)


def system_theme():
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return "Light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "Dark"
        except (ImportError, OSError):
            pass
    return "Dark"


def configure_fonts(root):
    available = {name.casefold(): name for name in tkfont.families(root)}
    def choose(role, fallback):
        return next((available[name.casefold()] for name in FONT_FAMILIES[role] if name.casefold() in available),
                    tkfont.nametofont(fallback, root=root).actual("family"))
    display, mono = choose("display", "TkDefaultFont"), choose("mono", "TkFixedFont")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        tkfont.nametofont(name, root=root).configure(family=mono)
    return display, mono


class StudioTheme:
    def __init__(self, root, manager, reduced_motion, mode="System"):
        self.root, self.manager, self.reduced_motion = root, manager, reduced_motion
        self.name = system_theme() if mode == "System" else mode
        self.palette = SimpleNamespace(**THEMES[self.name])
        self.control_palette = self.palette
        self.sprites = SpriteCache(root, limit=192)
        self.display, self.mono = configure_fonts(root)
        self._bindings = weakref.WeakKeyDictionary()
        self._views = weakref.WeakSet()
        self._geometry = weakref.WeakSet()
        self._fonts = {}
        self.scale, self.screen_width, self.screen_height = display_metrics(root)

    def px(self, value):
        return round(value * self.scale)

    def typeface(self, size, family=None, bold=False, italic=False):
        key = (size, family or self.mono, bold, italic)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(root=self.root, family=key[1], size=-max(1, self.px(size * 4 / 3)),
                                           weight="bold" if bold else "normal", slant="italic" if italic else "roman")
        return self._fonts[key]

    def update_scale(self):
        scale, self.screen_width, self.screen_height = display_metrics(self.root)
        if abs(scale - self.scale) < .005:
            return False
        self.scale = scale
        for (size, _, _, _), font in self._fonts.items():
            font.configure(size=-max(1, self.px(size * 4 / 3)))
        for widget in tuple(self._geometry):
            if widget.winfo_exists():
                widget._reflow()
        return True

    def bind(self, widget, **roles):
        self._bindings.setdefault(widget, {}).update(roles)
        self._apply_widget(widget, roles)
        return widget

    def register(self, view):
        self._views.add(view)

    def _apply_widget(self, widget, roles):
        widget.configure(**{option: getattr(self.palette, role) for option, role in roles.items()})

    def refresh(self):
        for widget, roles in tuple(self._bindings.items()):
            if widget.winfo_exists():
                self._apply_widget(widget, roles)
        for view in tuple(self._views):
            if view.winfo_exists():
                view.refresh_theme()

    def select(self, mode):
        if mode != "System" and mode not in THEMES:
            raise ValueError(f"Unknown theme: {mode}")
        target = system_theme() if mode == "System" else mode
        if target == self.name:
            return False
        self.name = target
        start, end = vars(self.palette).copy(), THEMES[target]
        self.manager.cancel_prefix("theme:warm:")
        if not self.reduced_motion.get():
            palette = SimpleNamespace(**end)
            views = [view for view in self._views if hasattr(view, "prepare_palette")]
            for index, view in enumerate(views):
                self.manager.call_later((index + 1) * 12, lambda item=view: item.prepare_palette(palette),
                                        key=f"theme:warm:{index}")
        def update(amount):
            colors = end if amount >= 1 else {role: lerp_color(start[role], color, amount) for role, color in end.items()}
            self.palette = SimpleNamespace(**colors)
            if amount >= 1:
                self.control_palette = self.palette
                self.manager.cancel_prefix("theme:warm:")
            self.refresh()
        self.manager.cancel("theme:fade")
        if self.reduced_motion.get():
            update(1)
        else:
            self.manager.tween("theme:fade", .25, update, easing=ease_in_out_quad)
        return True

    def frame(self, parent, role="BG", **kwargs):
        return self.bind(LayoutFrame(parent, self, bd=0, relief="flat", **kwargs), bg=role)

    def label(self, parent, text="", size=9, role="TEXT", bg="BG", bold=False, **kwargs):
        label = LayoutLabel(parent, self, text=text, font=self.typeface(size, bold=bold),
                         bd=0, relief="flat", **kwargs)
        return self.bind(label, fg=role, bg=bg)
