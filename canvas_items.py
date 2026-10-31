"""Retained canvas primitives; animation never recreates display items."""

import tkinter as tk


def rounded_points(x0, y0, x1, y1, radius=4):
    r = max(0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    return (x0, y1, x0, y0 + r, x0 + r * .3, y0 + r * .3, x0 + r, y0,
            x1 - r, y0, x1 - r * .3, y0 + r * .3, x1, y0 + r, x1, y1)


class RetainedCanvas(tk.Canvas):
    def __init__(self, parent, theme, manager, role="BG", **kwargs):
        super().__init__(parent, bg=getattr(theme.palette, role), highlightthickness=0, bd=0, **kwargs)
        self.theme, self.manager, self.bg_role = theme, manager, role
        self._positions, self._item_options = {}, {}
        self._closed = False
        self.key = f"view:{self}"
        theme.register(self)
        self.bind("<Configure>", lambda event: self.paint())
        self.bind("<Destroy>", self._dispose, add="+")

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
