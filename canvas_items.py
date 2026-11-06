"""Retained canvas primitives; animation never recreates display items."""

import tkinter as tk
from copy import copy
from layout import ScaledGeometry


def rounded_points(x0, y0, x1, y1, radius=4):
    r = max(0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    return (x0, y1, x0, y0 + r, x0 + r * .3, y0 + r * .3, x0 + r, y0,
            x1 - r, y0, x1 - r * .3, y0 + r * .3, x1, y0 + r, x1, y1)


class RetainedCanvas(ScaledGeometry, tk.Canvas):
    pixel_options = ScaledGeometry.pixel_options | {"width", "height"}

    def __init__(self, parent, theme, manager, role="BG", **kwargs):
        super().__init__(parent, bg=getattr(theme.palette, role), highlightthickness=0, bd=0,
                         **self._init_geometry(theme, kwargs))
        self.theme, self.manager, self.bg_role = theme, manager, role
        self._positions, self._item_options = {}, {}
        self._pixel_items = {}
        self._canvas_scale = theme.scale
        self._closed = False
        self.key = f"view:{self}"
        theme.register(self)
        self.bind("<Configure>", lambda event: self.paint())
        self.bind("<Destroy>", self._dispose, add="+")

    def winfo_width(self):
        return super().winfo_width() / self._ui_theme.scale

    def winfo_height(self):
        return super().winfo_height() / self._ui_theme.scale

    def _item_scale(self, options):
        scaled = dict(options)
        if isinstance(scaled.get("width"), (int, float)):
            scaled["width"] *= self._ui_theme.scale
        if isinstance(scaled.get("dash"), (tuple, list)):
            scaled["dash"] = tuple(max(1, self._ui_theme.px(value)) for value in scaled["dash"])
        return scaled

    def _create(self, kind, args, options):
        options = dict(options)
        if kind in ("line", "rectangle", "oval", "polygon", "arc"):
            options.setdefault("width", 1)
        coords = tuple(value * self._ui_theme.scale if isinstance(value, (int, float)) else value
                       for value in tk._flatten(args))
        item = super()._create(kind, coords, self._item_scale(options))
        self._pixel_items[item] = {key: value for key, value in options.items() if key in ("width", "dash")}
        return item

    def coords(self, *args):
        if len(args) > 1:
            return super().coords(args[0], *(value * self._ui_theme.scale for value in tk._flatten(args[1:])))
        return [value / self._ui_theme.scale for value in super().coords(*args)]

    def itemconfigure(self, item, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        pixels = {key: value for key, value in kwargs.items() if key in ("width", "dash")}
        if pixels:
            for target in self.find_withtag(item):
                self._pixel_items.setdefault(target, {}).update(pixels)
        return super().itemconfigure(item, cnf, **self._item_scale(kwargs))

    itemconfig = itemconfigure

    def bind(self, sequence=None, func=None, add=None):
        if func is None:
            return super().bind(sequence, func, add)
        def normalized(event):
            event = copy(event)
            for key in ("x", "y", "width", "height"):
                value = getattr(event, key, None)
                if isinstance(value, (int, float)):
                    setattr(event, key, value / self._ui_theme.scale)
            return func(event)
        return super().bind(sequence, normalized, add)

    def event_generate(self, sequence, **kwargs):
        for key in ("x", "y", "width", "height"):
            if key in kwargs:
                kwargs[key] = self._ui_theme.px(kwargs[key])
        return super().event_generate(sequence, **kwargs)

    def _reflow(self):
        super()._reflow()
        ratio = self._ui_theme.scale / self._canvas_scale
        super().scale("all", 0, 0, ratio, ratio)
        for item, options in self._pixel_items.items():
            if options:
                super().itemconfigure(item, **self._item_scale(options))
        self._canvas_scale = self._ui_theme.scale
        self._positions.clear()
        self._item_options.clear()
        self.paint()

    def position(self, item, *coords):
        coords = tuple(round(value, 2) for value in coords)
        if self._positions.get(item) != coords:
            self.coords(item, *coords)
            self._positions[item] = coords

    def style(self, item, **options):
        previous = self._item_options.setdefault(item, {})
        changes = {key: value for key, value in options.items() if previous.get(key) != value}
        if changes:
            self.itemconfig(item, **changes)
            previous.update(changes)

    def refresh_theme(self):
        self.configure(bg=getattr(self.theme.palette, self.bg_role))
        self.paint()

    def _dispose(self, event):
        if event.widget is self:
            self._closed = True
            self.manager.cancel_prefix(self.key + ":")

    def paint(self):
        pass
