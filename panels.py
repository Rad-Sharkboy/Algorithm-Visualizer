"""Retained instrument typography, meters, status, and navigation."""

import math

from canvas_items import RetainedCanvas
from motion import lerp_color


class DisplayTitle(RetainedCanvas):
    def __init__(self, parent, theme, manager, reduced_motion):
        super().__init__(parent, theme, manager, height=85)
        self.reduced_motion = reduced_motion
        self.text = "Sorting, made visible."
        self.progress = 1.0
        self._roman = theme.typeface(39, family=theme.display)
        self._italic = theme.typeface(39, family=theme.display, italic=True)
        self._first = self.create_text(0, 0, anchor="w", font=self._roman)
        self._last = self.create_text(0, 0, anchor="w", font=self._italic)

    def set_text(self, text):
        self.text = text
        self.paint()

    def launch(self):
        if not self.reduced_motion.get():
            self.manager.tween(self.key + ":intro", .65, self._intro)

    def _intro(self, amount):
        self.progress = amount
        self.paint()

    def settle(self):
        self.manager.cancel_prefix(self.key + ":")
        self.progress = 1
        self.paint()

    def paint(self):
        if self._closed:
            return
        p = self.theme.palette
        first = self.text[:-8] if self.text.endswith("visible.") else self.text
        last = "visible." if self.text.endswith("visible.") else ""
        size = 39 if self.winfo_width() > 720 else 33
        self._roman = self.theme.typeface(size, family=self.theme.display)
        self._italic = self.theme.typeface(size, family=self.theme.display, italic=True)
        y = 40 + (1 - self.progress) * 12
        color = lerp_color(p.BG, p.TEXT, self.progress)
        self.position(self._first, 0, y)
        self.position(self._last, self._roman.measure(first) / self.theme.scale, y)
        self.style(self._first, text=first, fill=color, font=self._roman)
        self.style(self._last, text=last, fill=color, font=self._italic)


class MeterRow(RetainedCanvas):
    def __init__(self, parent, theme, manager, reduced_motion):
        super().__init__(parent, theme, manager, height=88)
        self.reduced_motion = reduced_motion
        self.values = {name: 0.0 for name in ("comparisons", "writes", "steps", "elapsed")}
        self.targets = self.values.copy()
        self._labels, self._numbers, self._separators = [], [], []
        for label in ("COMPARISONS", "ARRAY WRITES", "VISUAL STEPS", "ACTIVE / SEC"):
            self._labels.append(self.create_text(0, 0, anchor="nw", text=" ".join(label), font=theme.typeface(8)))
            self._numbers.append(self.create_text(0, 0, anchor="nw", font=theme.typeface(27)))
        self._separators = [self.create_line(0, 0, 0, 0) for _ in range(3)]
        self._rule = self.create_line(0, 0, 0, 0)

    def set(self, **values):
        for key, value in values.items():
            value = float(value)
            if self.targets[key] == value:
                continue
            self.targets[key] = value
            start = self.values[key]
            def update(amount, name=key, before=start, target=value):
                self.values[name] = before + (target - before) * amount
                self.paint()
            if self.reduced_motion.get() or value == 0:
                self.manager.cancel(self.key + ":" + key)
                update(1)
            else:
                self.manager.tween(self.key + ":" + key, .2, update)

    def settle(self):
        self.manager.cancel_prefix(self.key + ":")
        self.values.update(self.targets)
        self.paint()

    def paint(self):
        if self._closed:
            return
        p, w = self.theme.palette, self.winfo_width()
        for index, key in enumerate(self.values):
            x = index * w / 4 + (18 if index else 0)
            self.position(self._labels[index], x, 8)
            self.style(self._labels[index], fill=p.MUTED)
            self.position(self._numbers[index], x, 26)
            number = f"{self.values[key]:.1f}" if key == "elapsed" else f"{round(self.values[key]):,}"
            self.style(self._numbers[index], text=number, fill=p.TEXT)
            if index:
                self.position(self._separators[index - 1], index * w / 4, 9, index * w / 4, 72)
                self.style(self._separators[index - 1], fill=p.BORDER)
        self.position(self._rule, 0, 87, w, 87)
        self.style(self._rule, fill=p.BORDER)


class StatusLamp(RetainedCanvas):
    def __init__(self, parent, theme, manager, reduced_motion):
        super().__init__(parent, theme, manager, width=128, height=28)
        self.reduced_motion = reduced_motion
        self.state = "ready"
        self.phase = 0.0
        self._dot = self.create_oval(0, 0, 0, 0)
        self._label = self.create_text(0, 0, anchor="w", font=theme.typeface(9))
        self.bind("<Unmap>", lambda event: self.manager.cancel(self.key + ":pulse"))
        self.bind("<Map>", lambda event: self.set(self.state))

    def set(self, state):
        self.state = state
        if state == "running" and not self.reduced_motion.get() and self.winfo_ismapped():
            self.manager.loop(self.key + ":pulse", self._pulse, interval=32)
        else:
            self.manager.cancel(self.key + ":pulse")
        self.paint()

    def _pulse(self, now, dt):
        self.phase = (self.phase + dt / 1.8) % 1
        self.paint()

    def paint(self):
        if self._closed:
            return
        p = self.theme.palette
        color = p.SETTLED if self.state == "done" else p.ACCENT if self.state in ("running", "finishing") else p.MUTED
        if self.state == "running" and not self.reduced_motion.get():
            color = lerp_color(p.BG, color, .5 + .5 * (1 + math.sin(self.phase * math.tau)) / 2)
        text = {"done": "COMPLETE", "finishing": "SETTLING", "not_found": "NOT FOUND"}.get(self.state, self.state.upper())
        self.position(self._dot, 5, 11, 11, 17)
        self.style(self._dot, fill=color, outline="")
        self.position(self._label, 21, 14)
        self.style(self._label, fill=color, text=text)


class Navigation(RetainedCanvas):
    def __init__(self, parent, theme, manager, reduced_motion, command):
        super().__init__(parent, theme, manager, width=186, height=320, takefocus=True, cursor="hand2")
        self.reduced_motion, self.command = reduced_motion, command
        self.names = []
        self.selected = 0
        self.indicator = 0.0
        self.hover = [0.0] * 13
        self.intro = [1.0] * 13
        self._hovered = None
        self._focused = False
        self._lines = [self.create_text(0, 0, anchor="w", font=theme.typeface(10)) for _ in range(13)]
        self._numbers = [self.create_text(0, 0, anchor="w", font=theme.typeface(8)) for _ in range(13)]
        self._line = self.create_rectangle(0, 0, 0, 0, outline="")
        self._dot = self.create_oval(0, 0, 0, 0, outline="")
        self._focus_line = self.create_rectangle(0, 0, 0, 0, fill="", state="hidden")
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda event: self._hover(None))
        self.bind("<ButtonRelease-1>", self._click)
        self.bind("<FocusIn>", lambda event: self._focus(True))
        self.bind("<FocusOut>", lambda event: self._focus(False))
        for key in ("Up", "Down", "Return", "space"):
            self.bind(f"<KeyPress-{key}>", self._key)

    def set_names(self, names):
        self.manager.cancel_prefix(self.key + ":")
        self.names = names
        self.configure(height=len(names) * 30 + 10)
        self.hover = [0.0] * 13
        self.intro = [1.0] * 13
        self.selected = 0
        self.indicator = 0
        self.paint()

    def select(self, name):
        if name not in self.names:
            return
        self.selected = self.names.index(name)
        start = self.indicator
        def update(amount):
            self.indicator = start + (self.selected - start) * amount
            self.paint()
        if self.reduced_motion.get():
            self.manager.cancel(self.key + ":indicator")
            update(1)
        else:
            self.manager.tween(self.key + ":indicator", .24, update)

    def launch(self):
        if self.reduced_motion.get():
            return
        for index in range(len(self.names)):
            self.intro[index] = 0
            def update(amount, row=index):
                self.intro[row] = amount
                self.paint()
            self.manager.tween(self.key + f":intro:{index}", .28, update, delay=index * .04)
        self.paint()

    def settle(self):
        self.manager.cancel_prefix(self.key + ":")
        self.intro = [1.0] * 13
        self.indicator = float(self.selected)
        self.paint()

    def _motion(self, event):
        row = int((event.y - 5) // 30)
        self._hover(row if 0 <= row < len(self.names) else None)

    def _hover(self, index):
        if index == self._hovered:
            return
        old, self._hovered = self._hovered, index
        for row in (old, index):
            if row is None:
                continue
            start, target = self.hover[row], float(row == index)
            def update(amount, i=row, a=start, b=target):
                self.hover[i] = a + (b - a) * amount
                self.paint()
            if self.reduced_motion.get():
                update(1)
            else:
                self.manager.tween(self.key + f":hover:{row}", .12, update)

    def _click(self, event):
        row = int((event.y - 5) // 30)
        if 0 <= row < len(self.names):
            self.focus_set()
            self.command(self.names[row])

    def _key(self, event):
        if event.keysym in ("Up", "Down"):
            index = max(0, min(len(self.names) - 1, self.selected + (-1 if event.keysym == "Up" else 1)))
            self.command(self.names[index])
        elif self.names:
            self.command(self.names[self.selected])
        return "break"

    def _focus(self, value):
        self._focused = value
        self.paint()

    def paint(self):
        if self._closed:
            return
        p = self.theme.palette
        for row in range(13):
            for item in (self._lines[row], self._numbers[row]):
                self.style(item, state="normal" if row < len(self.names) else "hidden")
            if row >= len(self.names):
                continue
            amount = self.intro[row]
            x = 37 + 4 * self.hover[row] + (1 - amount) * 10
            y = row * 30 + 20
            color = lerp_color(p.ACCENT, p.TEXT, self.hover[row] * .2) if row == self.selected else lerp_color(p.MUTED, p.TEXT, self.hover[row])
            self.position(self._numbers[row], 15, y)
            self.position(self._lines[row], x, y)
            self.style(self._numbers[row], text=f"{row + 1:02}", fill=lerp_color(p.BG, p.MUTED, amount))
            self.style(self._lines[row], text=self.names[row].replace(" Sort", "").replace(" Search", ""),
                       fill=lerp_color(p.BG, color, amount))
        yy = self.indicator * 30 + 20
        self.position(self._line, 0, yy - 10, 2, yy + 10)
        self.position(self._dot, 7, yy - 2, 11, yy + 2)
        self.style(self._line, fill=p.ACCENT)
        self.style(self._dot, fill=p.ACCENT)
        self.position(self._focus_line, 5, yy - 13, self.winfo_width() - 2, yy + 13)
        self.style(self._focus_line, outline=p.BORDER, state="normal" if self._focused else "hidden")
