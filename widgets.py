"""Orbital playback and glass motion controls drawn entirely in Tk."""

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


class OrbitButton(tk.Canvas):
    """Keyboard-operable orbital playback dial with a morphing icon."""

    def __init__(self, parent, theme, command, reduced_motion, text="Run", width=184, height=64):
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
        self._phase = 0.0
        self._pointer = .5
        self._last_tick = time.perf_counter()
        self._ripple = 1.0
        self._icon = self._icon_from = self._icon_target = 0.0
        self._effect_started = time.perf_counter()
        self.bind("<Configure>", self._paint)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Motion>", self._move)
        self.bind("<Unmap>", lambda event: self._cancel_effect())
        self.bind("<Map>", lambda event: self._start_effect())
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
        previous_state = self._state
        custom = False
        for name in ("text", "state", "command"):
            if name in kwargs:
                value = kwargs.pop(name)
                setattr(self, "command" if name == "command" else f"_{name}", value)
                custom = True
        result = super().configure(cnf, **kwargs) if cnf is not None or kwargs or not custom else None
        if custom and hasattr(self, "theme"):
            if previous_state != self._state:
                self._pressed = False
                super().configure(cursor="arrow" if self._state == "disabled" else "hand2")
                self._start_effect()
            else:
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
        changed = state != self._playback
        self._playback = state
        self._text = {"running": "Pause", "paused": "Resume", "done": "Replay"}.get(state, "Run")
        if changed or target != self._icon_target:
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
            self._ripple = 1.0
            self._icon = self._icon_target
        else:
            self._start_effect()
        self._paint()

    def _enter(self, event):
        self._hovered = True
        self._start_effect()

    def _move(self, event):
        if not self.reduced_motion.get() and self._state != "disabled":
            self._pointer = max(0, min(1, event.x / max(1, self.winfo_width())))
            self._paint()

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
        if self._closed:
            return
        self._cancel_effect()
        self._icon_from = self._icon
        self._effect_started = self._last_tick = time.perf_counter()
        if self.reduced_motion.get() or self._state == "disabled":
            self._ripple = 1.0
            self._icon = self._icon_target
            self._paint()
        else:
            self._animate_effect()

    def _animate_effect(self):
        self._effect_id = None
        if self._closed:
            return
        now = time.perf_counter()
        elapsed = now - self._effect_started
        self._icon = self._icon_from + (self._icon_target - self._icon_from) * ease(elapsed / .22)
        active = self._state != "disabled" and self._playback == "running"
        velocity = .9 if active else max(0, 1 - elapsed / .6) * 2
        self._phase = (self._phase + min(.1, now - self._last_tick) * velocity) % math.tau
        self._last_tick = now
        if self._ripple < 1:
            self._ripple = min(1.0, elapsed / .4)
        self._paint()
        if (elapsed < .6 or active) and self.winfo_ismapped():
            self._effect_id = self.after(33, self._animate_effect)

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
        disabled = self._state == "disabled"
        accent = p.MUTED if disabled else p.ACCENT
        second = p.MUTED if disabled else p.PURPLE
        bg = str(self.cget("bg"))
        depth = 2 if self._pressed else 0
        top, bottom = 7 + depth, h - 9 + depth
        cy = (top + bottom) / 2
        cx, radius = 34, min(24, (bottom - top) / 2)
        left, right = 10, w - 6
        cut = 13
        hull = (left + 20, top, right - cut, top, right, top + cut,
                right, bottom - cut, right - cut, bottom, left + 20, bottom,
                left, cy + 12, left, cy - 12)
        shadow = [value + (0 if i % 2 == 0 else 3 - depth / 2)
                  for i, value in enumerate(hull)]
        self.create_polygon(*shadow, fill=blend(bg, p.ACCENT, .18), outline="")
        self.create_polygon(*hull, fill=p.INSET, outline=p.BORDER, width=1)
        for y in range(int(top + 1), int(bottom)):
            inset = max(0, cut - min(y - top, bottom - y))
            fraction = (y - top) / (bottom - top)
            color = blend(p.GLASS_TOP, p.INSET, fraction * .85)
            self.create_line(33, y, right - inset - 1, y, fill=color)
            if self._hovered and not disabled:
                light = .12 * (1 - abs(fraction - .25))
                x = 70 + self._pointer * (right - 80)
                for band in range(-3, 4):
                    a = max(34, x + band * 9 - fraction * 18)
                    b = min(right - inset - 2, a + 9)
                    if b > a:
                        self.create_line(a, y, b, y, fill=blend(color, p.SHINE, light * (1 - abs(band) / 4)))
        self.create_line(53, top + 1, right - cut, top + 1, right - 1, top + cut,
                         fill=blend(p.BORDER, second, .55), width=1)
        self.create_line(56, bottom - 1, right - cut, bottom - 1, right - 1, bottom - cut,
                         fill=blend(p.BORDER, accent, .65), width=1)
        for index in range(5):
            x = right - 11 - index * 4
            self.create_line(x - 2, bottom - 4, x, bottom - 7,
                             fill=blend(p.BORDER, accent, .45 if index == 0 else .12))
        if self._focused:
            focus = (left + 20, top - 4, right - cut + 2, top - 4, right + 4, top + cut - 2,
                     right + 4, bottom - cut + 2, right - cut + 2, bottom + 4,
                     left + 20, bottom + 4, left - 4, cy + 14, left - 4, cy - 14)
            self.create_polygon(*focus, fill="", outline=accent, width=2, tags="focus-ring")
        self.create_oval(cx - radius - 3, cy - radius - 3, cx + radius + 3, cy + radius + 3,
                         fill=bg, outline=blend(p.BORDER, accent, .35))
        self.create_oval(cx - radius + 1, cy - radius + 1, cx + radius - 1, cy + radius - 1,
                         fill=p.INSET, outline=p.BORDER)
        phase = self._phase
        for index in range(64):
            angle = index * math.tau / 64
            following = (index + 1) * math.tau / 64
            glow = (.5 + .5 * math.cos(angle - phase)) ** 3
            tint = blend(second, accent, .5 + .5 * math.sin(angle + .5))
            color = blend(p.BORDER, tint, .25 + .75 * glow)
            self.create_line(cx + radius * math.cos(angle), cy + radius * math.sin(angle),
                             cx + radius * math.cos(following), cy + radius * math.sin(following),
                             fill=color, width=2, tags="orbit-rim")
        for tilt, color, direction in ((-.55, accent, 1), (.55, second, -1)):
            points = []
            for index in range(49):
                angle = index * math.tau / 48
                x, y = (radius - 4) * math.cos(angle), (radius - 12) * math.sin(angle)
                points.extend((cx + x * math.cos(tilt) - y * math.sin(tilt),
                               cy + x * math.sin(tilt) + y * math.cos(tilt)))
            self.create_line(*points, fill=blend(p.INSET, color, .40), width=1, smooth=True)
            angle = phase * direction + tilt
            x, y = (radius - 4) * math.cos(angle), (radius - 12) * math.sin(angle)
            px = cx + x * math.cos(tilt) - y * math.sin(tilt)
            py = cy + x * math.sin(tilt) + y * math.cos(tilt)
            self.create_oval(px - 3, py - 3, px + 3, py + 3,
                             fill=blend(p.INSET, color, .35), outline="")
            self.create_oval(px - 1.5, py - 1.5, px + 1.5, py + 1.5,
                             fill=color, outline="", tags="orbit-particle")
        self.create_oval(cx - 11, cy - 11, cx + 11, cy + 11,
                         fill=blend(p.INSET, p.GLASS_TOP, .55), outline=blend(p.BORDER, accent, .25))
        play = ((-4, -6, 1, -3, 1, 3, -4, 6), (1, -3, 6, 0, 6, 0, 1, 3))
        pause = ((-5, -6, -2, -6, -2, 6, -5, 6), (2, -6, 5, -6, 5, 6, 2, 6))
        for start, end in zip(play, pause):
            points = [(a + (b - a) * self._icon) * (.9 if self._pressed else 1) +
                      (cx if i % 2 == 0 else cy)
                      for i, (a, b) in enumerate(zip(start, end))]
            self.create_polygon(*points, fill=accent, outline="", tags="playback-icon")
        if self._ripple < 1 and not disabled:
            ripple_radius = 12 + 10 * ease(self._ripple)
            self.create_oval(cx - ripple_radius, cy - ripple_radius, cx + ripple_radius, cy + ripple_radius,
                             outline=blend(p.INSET, accent, .6 * (1 - self._ripple)), width=2)
        self.create_text(69, cy - 6, text=self._text, anchor="w", fill=p.MUTED if disabled else p.TEXT,
                         font=(self.theme.font, 13, "bold"), tags="playback-label")
        caption = {"running": "IN MOTION", "paused": "CONTINUE", "done": "ONCE MORE"}.get(self._playback, "PRESS TO PLAY")
        if disabled:
            caption = "UNAVAILABLE"
        self.create_text(70, cy + 12, text=caption, anchor="w", fill=p.MUTED,
                         font=(self.theme.mono, 7), tags="playback-caption")
        self.create_oval(right - 20, cy - 3, right - 14, cy + 3,
                         fill=accent if self._playback == "running" and not disabled else p.BORDER,
                         outline="", tags="playback-status")

class MotionToggle(OrbitButton):
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
