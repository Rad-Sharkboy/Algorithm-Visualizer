"""Glass-inspired controls drawn in Tk: no images, native blur, or dependencies."""

import math
import time
import tkinter as tk

from motion import blend, ease


def rounded_panel(canvas, x0, y0, x1, y1, radius, **options):
    radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    points = []
    for cx, cy, start in ((x1 - radius, y0 + radius, -90),
                          (x1 - radius, y1 - radius, 0),
                          (x0 + radius, y1 - radius, 90),
                          (x0 + radius, y0 + radius, 180)):
        for step in range(9):
            angle = math.radians(start + step * 90 / 8)
            points.extend((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return canvas.create_polygon(*points, **options)


class GlassButton(tk.Canvas):
    """Keyboard-operable playback button with clipped sheen and a morphing icon."""

    def __init__(self, parent, theme, command, reduced_motion, text="Run", width=132, height=48):
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, takefocus=True, cursor="hand2")
        self.theme = theme
        self.command = command
        self.reduced_motion = reduced_motion
        self._text = text
        self._state = "normal"
        self._playback = "ready"
        self._hovered = self._pressed = self._focused = False
        self._closed = False
        self._effect_id = None
        self._shine = 1.0
        self._ripple = 1.0
        self._icon = self._icon_from = self._icon_target = 0.0
        self._effect_started = time.perf_counter()
        self.bind("<Configure>", self._paint)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        for key in ("space", "Return"):
            self.bind(f"<KeyPress-{key}>", self._key_press)
            self.bind(f"<KeyRelease-{key}>", self._key_release)
        self.bind("<FocusIn>", lambda event: self._focus(True))
        self.bind("<FocusOut>", lambda event: self._focus(False))
        self.bind("<Destroy>", self._dispose, add="+")

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        custom = False
        for name in ("text", "state", "command"):
            if name in kwargs:
                value = kwargs.pop(name)
                setattr(self, "command" if name == "command" else f"_{name}", value)
                custom = True
        result = super().configure(cnf, **kwargs) if cnf is not None or kwargs or not custom else None
        if custom and hasattr(self, "theme"):
            self._paint()
        return result

    config = configure

    def cget(self, key):
        if key in ("text", "state"):
            return getattr(self, f"_{key}")
        return super().cget(key)

    def invoke(self):
        if not self._closed and self._state != "disabled":
            self._ripple = 0.0
            result = self.command()
            self._start_effect()
            return result

    def set_playback(self, state):
        target = 1.0 if state == "running" else 0.0
        self._playback = state
        self._text = {"running": "Pause", "paused": "Resume", "done": "Replay"}.get(state, "Run")
        if target != self._icon_target:
            self._icon_from, self._icon_target = self._icon, target
            self._start_effect()
        else:
            self._paint()

    def refresh_theme(self):
        super().configure(bg=self.master.cget("bg"))
        self._paint()

    def motion_changed(self):
        if self.reduced_motion.get():
            self._cancel_effect()
            self._shine = self._ripple = 1.0
            self._icon = self._icon_target
        self._paint()

    def _enter(self, event):
        self._hovered = True
        self._shine = 0.0
        self._start_effect()

    def _leave(self, event):
        self._hovered = False
        self._paint()

    def _press(self, event):
        if self._state != "disabled":
            self.focus_set()
            self._pressed = True
            self._paint()

    def _release(self, event):
        armed, self._pressed = self._pressed, False
        if armed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()
        self._paint()

    def _key_press(self, event):
        self._press(event)
        return "break"

    def _key_release(self, event):
        armed, self._pressed = self._pressed, False
        if armed:
            self.invoke()
        self._paint()
        return "break"

    def _focus(self, focused):
        self._focused = focused
        if not focused:
            self._pressed = False
        self._paint()

    def _start_effect(self):
        self._cancel_effect()
        self._icon_from = self._icon
        self._effect_started = time.perf_counter()
        if self.reduced_motion.get():
            self.motion_changed()
        else:
            self._animate_effect()

    def _animate_effect(self):
        self._effect_id = None
        if self._closed:
            return
        elapsed = time.perf_counter() - self._effect_started
        self._icon = self._icon_from + (self._icon_target - self._icon_from) * ease(elapsed / .22)
        if self._shine < 1:
            self._shine = min(1.0, elapsed / .6)
        if self._ripple < 1:
            self._ripple = min(1.0, elapsed / .4)
        self._paint()
        if elapsed < .6:
            self._effect_id = self.after(16, self._animate_effect)

    def _cancel_effect(self):
        if self._effect_id is not None:
            self.after_cancel(self._effect_id)
            self._effect_id = None

    def _dispose(self, event):
        if event.widget is self:
            self._closed = True
            self._cancel_effect()

    def _paint(self, event=None):
        if self._closed:
            return
        self.delete("all")
        p = self.theme.palette
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        offset = 1 if self._pressed else 0
        x0, y0, x1, y1, radius = 4, 3 + offset, w - 4, h - 7 + offset, 12
        bg = str(self.cget("bg"))
        rounded_panel(self, 4, 7, w - 4, h - 3, radius,
                      fill=blend(bg, p.ACCENT, .16), outline="")
        # Each scanline is clipped to a rounded silhouette. A moving diagonal
        # reflection stays inside the surface, including its curved corners.
        for row in range(int(y1 - y0) + 1):
            edge = min(row, y1 - y0 - row)
            inset = radius - math.sqrt(max(0, radius * radius - (radius - edge) ** 2)) if edge < radius else 0
            left, right, y = x0 + inset, x1 - inset, y0 + row
            color = blend(p.GLASS_TOP, p.GLASS_BOTTOM, row / (y1 - y0))
            if self._hovered or self._pressed:
                color = blend(color, p.ACCENT, .09 if self._hovered else .15)
            self.create_line(left, y, right, y, fill=color)
            if self._shine < 1:
                center = (w + 90) * self._shine - 45 - row * .6
                for stripe in range(-3, 4):
                    a, b = max(left, center + stripe * 5), min(right, center + (stripe + 1) * 5)
                    if b > a:
                        self.create_line(a, y, b, y, fill=blend(color, p.SHINE, .16 * (1 - abs(stripe) / 4)))
        rounded_panel(self, x0, y0, x1, y1, radius, fill="",
                      outline=blend(p.ACCENT, p.SHINE, .25) if self._hovered else p.SELECT_BORDER)
        self.create_line(x0 + radius, y0 + 1, x1 - radius, y0 + 1,
                         fill=blend(p.GLASS_TOP, p.SHINE, .65))
        if self._focused:
            rounded_panel(self, 1, 0, w - 1, h - 4, 15, fill="", outline=p.ACCENT, width=2)
        if self._ripple < 1:
            r = 4 + 13 * ease(self._ripple)
            self.create_oval(w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r,
                             outline=blend(p.GLASS_BOTTOM, p.ACCENT, (1 - self._ripple) * .5), width=2)
        color = p.MUTED if self._state == "disabled" else p.ACCENT
        ix, iy = 21, (y0 + y1) / 2 - 9
        play = ((0, 0, 7, 4, 7, 14, 0, 18), (7, 4, 15, 9, 15, 9, 7, 14))
        pause = ((0, 1, 5, 1, 5, 17, 0, 17), (10, 1, 15, 1, 15, 17, 10, 17))
        for start, end in zip(play, pause):
            points = [a + (b - a) * self._icon + (ix if i % 2 == 0 else iy)
                      for i, (a, b) in enumerate(zip(start, end))]
            self.create_polygon(*points, fill=color, outline="")
        self.create_text(w / 2 + 12, (y0 + y1) / 2, text=self._text,
                         fill=p.MUTED if self._state == "disabled" else p.TEXT,
                         font=(self.theme.font, 10, "bold"))


class MotionToggle(GlassButton):
    """A focusable glass pill for the reduced-motion setting."""

    def __init__(self, parent, theme, variable, command):
        self.variable = variable
        self.on_change = command
        super().__init__(parent, theme, self._toggle, variable, width=188, height=34)
        self._icon = self._icon_target = float(variable.get())
        self._trace = variable.trace_add("write", self._variable_changed)

    def _variable_changed(self, *args):
        self._icon_target = float(self.variable.get())
        self._start_effect()

    def _dispose(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)
        super()._dispose(event)

    def _toggle(self):
        self.variable.set(not self.variable.get())
        self.on_change()

    def _paint(self, event=None):
        if self._closed:
            return
        self.delete("all")
        p = self.theme.palette
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        on = self.variable.get()
        rounded_panel(self, 2, 2, w - 2, h - 2, 12, fill=p.SELECT if on else p.INSET,
                      outline=p.ACCENT if self._focused or self._hovered else p.BORDER)
        self.create_text(13, h / 2, text="Reduced motion", anchor="w",
                         fill=p.TEXT, font=(self.theme.font, 9))
        x = w - 47
        rounded_panel(self, x, 9, x + 32, h - 9, 8,
                      fill=p.ACCENT if on else p.BORDER, outline="")
        center = x + 8 + 16 * self._icon
        self.create_oval(center - 5, h / 2 - 5, center + 5, h / 2 + 5,
                         fill=p.ON_ACCENT if on else p.TEXT, outline="")
