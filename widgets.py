"""Frosted playback controls and sliders drawn entirely in Tk."""

import math
import struct
import zlib
import time
import tkinter as tk
from tkinter import font as tkfont

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


def frosted_image(canvas, width, height, radius, top, bottom, edge, background, shadow=.20):
    width, height = max(2, round(width)), max(2, round(height))
    key = (width, height, radius, top, bottom, edge, background, shadow)
    cache = canvas._surface_cache
    if key in cache:
        return cache[key]
    colors = [tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
              for color in (top, bottom, edge, background)]
    upper, lower, rim, bg = colors
    pad = 4
    half_w, half_h = width / 2 - pad, height / 2 - pad - 1
    radius = min(radius, half_w, half_h)
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            dx = abs(x + .5 - width / 2) - half_w + radius
            dy = abs(y + .5 - (height / 2 - 1)) - half_h + radius
            distance = math.hypot(max(0, dx), max(0, dy)) + min(max(dx, dy), 0) - radius
            coverage = max(0, min(1, .5 - distance))
            shade = shadow * math.exp(-max(0, distance) ** 2 / 5) * max(0, min(1, y / height))
            base = [value * (1 - shade) for value in bg]
            if coverage:
                amount = max(0, min(1, (y - pad) / max(1, height - 2 * pad)))
                sheen = .10 * math.exp(-((amount - .18) / .22) ** 2)
                border = max(0, min(1, distance + 1.1)) * (.8 - .35 * amount)
                face = [a + (b - a) * amount for a, b in zip(upper, lower)]
                face = [value + (255 - value) * sheen for value in face]
                face = [value + (outline - value) * border for value, outline in zip(face, rim)]
                base = [a + (b - a) * coverage for a, b in zip(base, face)]
            pixels.extend(max(0, min(255, round(value))) for value in base)
    data = f"P6\n{width} {height}\n255\n".encode() + pixels
    texture = tk.PhotoImage(master=canvas, data=data, format="PPM")
    cache[key] = texture
    if len(cache) > 24:
        del cache[next(iter(cache))]
    return texture


def playback_glyph(canvas, amount, color):
    amount = round(amount * 20) / 20
    key = (amount, color)
    if key in canvas._glyph_cache:
        return canvas._glyph_cache[key]
    rgb = bytes(int(color[i:i + 2], 16) for i in (1, 3, 5))
    play = ((-3, -5, 1, -2.5, 1, 2.5, -3, 5), (1, -2.5, 5, 0, 5, 0, 1, 2.5))
    pause = ((-4, -4.5, -1.5, -4.5, -1.5, 4.5, -4, 4.5),
             (1.5, -4.5, 4, -4.5, 4, 4.5, 1.5, 4.5))
    polygons = []
    for start, end in zip(play, pause):
        points = [a + (b - a) * amount for a, b in zip(start, end)]
        polygons.append(list(zip(points[::2], points[1::2])))
    raw = bytearray()
    for y in range(24):
        raw.append(0)
        for x in range(24):
            px, py = x - 11.5, y - 11.5
            coverage = max(0, min(1, 1.3 - abs(math.hypot(px, py) - 10)))
            if abs(px) < 6 and abs(py) < 6:
                for polygon in polygons:
                    crosses, distances = [], []
                    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
                        dx, dy = bx - ax, by - ay
                        length = dx * dx + dy * dy
                        if length:
                            t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length))
                            distances.append(math.hypot(px - ax - t * dx, py - ay - t * dy))
                            crosses.append(dx * (py - ay) - dy * (px - ax))
                    inside = all(v >= 0 for v in crosses) or all(v <= 0 for v in crosses)
                    distance = min(distances)
                    coverage = max(coverage, max(0, min(1, .5 + distance if inside else .5 - distance)))
            raw.extend(rgb + bytes((round(255 * coverage),)))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 24, 24, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
    image = tk.PhotoImage(master=canvas, data=png, format='PNG')
    canvas._glyph_cache[key] = image
    if len(canvas._glyph_cache) > 48:
        del canvas._glyph_cache[next(iter(canvas._glyph_cache))]
    return image


class FrostButton(tk.Canvas):
    """A frosted playback pill with keyboard activation and a morphing icon."""

    def __init__(self, parent, theme, command, reduced_motion, text="Run", width=148, height=54):
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
        self._surface_cache = {}
        self._glyph_cache = {}
        self._label_font = tkfont.Font(root=self, family=theme.font, size=12, weight="bold")
        self._press_amount = self._press_from = 0.0
        self._icon = self._icon_from = self._icon_target = 0.0
        self._effect_started = time.perf_counter()
        self.bind("<Configure>", self._paint)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
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
        self._surface_cache.clear()
        self._paint()

    def motion_changed(self):
        if self.reduced_motion.get():
            self._cancel_effect()
            self._press_amount = float(self._pressed)
            self._icon = self._icon_target
        else:
            self._start_effect()
        self._paint()

    def _enter(self, event):
        self._hovered = True
        self._start_effect()

    def _leave(self, event):
        self._hovered = False
        self._paint()

    def _press(self, event):
        if self._state != "disabled":
            self.focus_set()
            self._pressed = True
            self._start_effect()

    def _release(self, event):
        armed, self._pressed = self._pressed, False
        if armed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()
        self._start_effect()

    def _key_press(self, event):
        self._press(event)
        return "break"

    def _key_release(self, event):
        armed, self._pressed = self._pressed, False
        if armed:
            self.invoke()
        self._start_effect()
        return "break"

    def _focus(self, focused):
        self._focused = focused
        if not focused:
            self._pressed = False
        self._start_effect()

    def _start_effect(self):
        if self._closed:
            return
        self._cancel_effect()
        self._icon_from = self._icon
        self._press_from = self._press_amount
        self._effect_started = time.perf_counter()
        if self.reduced_motion.get() or self._state == "disabled":
            self._press_amount = float(self._pressed)
            self._icon = self._icon_target
            self._paint()
        else:
            self._animate_effect()

    def _animate_effect(self):
        self._effect_id = None
        if self._closed:
            return
        elapsed = time.perf_counter() - self._effect_started
        progress = ease(elapsed / .22)
        self._icon = self._icon_from + (self._icon_target - self._icon_from) * progress
        self._press_amount = self._press_from + (float(self._pressed) - self._press_from) * progress
        self._paint()
        if elapsed < .22 and self.winfo_ismapped():
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
        disabled = self._state == "disabled"
        bg = str(self.cget("bg"))
        amount = self._press_amount
        width, height = w - 4 * amount, h - 3 * amount
        top, bottom = p.GLASS_TOP, p.GLASS_BOTTOM
        if self._hovered and not disabled:
            top = blend(top, p.SHINE, .08)
            bottom = blend(bottom, p.SHINE, .04)
        if disabled:
            top, bottom = blend(bg, top, .4), blend(bg, bottom, .4)
        self._surface = frosted_image(self, width, height, height / 2, top, bottom,
                                      p.FROST_EDGE, bg, .10 if self.theme.name == "Light" else .24)
        self.create_image(w / 2, h / 2 + amount, image=self._surface, tags="button-surface")
        if self._focused:
            rounded_panel(self, 3, 3, w - 3, h - 3, h / 2 - 3, fill="",
                          outline=p.SLIDER_FILL, width=2, tags="focus-ring")
        color = p.MUTED if disabled else p.TEXT
        label_width = self._label_font.measure(self._text)
        left = (w - label_width - 32) / 2
        cx, cy = left + 10, h / 2 - 1 + amount
        self._glyph = playback_glyph(self, self._icon, color)
        self.create_image(cx, cy, image=self._glyph, tags="playback-icon")
        self.create_text(left + 32, cy, text=self._text, anchor="w", fill=color,
                         font=self._label_font, tags="playback-label")


class MotionToggle(FrostButton):
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


class FrostSlider(tk.Canvas):
    def __init__(self, parent, theme, variable, command, reduced_motion,
                 from_=0, to=100, length=176, step=1):
        super().__init__(parent, width=length, height=36, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, takefocus=True, cursor="hand2")
        self.theme = theme
        self.variable = variable
        self.command = command
        self.reduced_motion = reduced_motion
        self.minimum, self.maximum, self.step = float(from_), float(to), float(step)
        if self.maximum <= self.minimum or self.step <= 0:
            raise ValueError("Slider bounds must increase and its step must be positive.")
        self._state = "normal"
        self._closed = self._syncing = False
        self._dragging = self._hovered = self._focused = False
        self._drag_offset = 0.0
        self._effect_id = None
        self._expansion = self._expansion_from = self._expansion_target = 0.0
        self._surface_cache = {}
        self._last_value = None
        self._trace = variable.trace_add("write", self._variable_changed)
        self.bind("<Configure>", self._paint)
        self.bind("<Enter>", lambda event: self._hover(True))
        self.bind("<Leave>", lambda event: self._hover(False))
        self.bind("<FocusIn>", lambda event: self._focus(True))
        self.bind("<FocusOut>", lambda event: self._focus(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Unmap>", self._unmap)
        self.bind("<Destroy>", self._dispose)
        for key in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
            self.bind(f"<KeyPress-{key}>", self._key)
        self.bind("<KeyPress-space>", lambda event: "break")
        self._variable_changed()

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        state = kwargs.pop("state", None)
        if state is not None:
            self._state = state
            if state == "disabled":
                self._end_drag()
                self._hovered = False
                self._cancel_effect()
                self._expansion = 0.0
            super().configure(cursor="arrow" if state == "disabled" else "hand2")
        result = super().configure(cnf, **kwargs) if cnf is not None or kwargs or state is None else None
        if state is not None:
            self._paint()
        return result

    config = configure

    def cget(self, key):
        if key == "state":
            return self._state
        return super().cget(key)

    def get(self):
        return self._last_value

    def set(self, value):
        if not self._closed:
            self.variable.set(value)

    def _variable_changed(self, *args):
        if self._closed or self._syncing:
            return
        invalid = False
        try:
            raw = float(self.variable.get())
            if not math.isfinite(raw):
                invalid = True
                raw = self.minimum
        except (ValueError, tk.TclError):
            invalid = True
            raw = self.minimum
        value = self.minimum + round((raw - self.minimum) / self.step) * self.step
        value = max(self.minimum, min(self.maximum, value))
        if invalid or raw != value:
            self._syncing = True
            try:
                self.variable.set(value)
            finally:
                self._syncing = False
        changed = value != self._last_value
        self._last_value = value
        self._paint()
        if changed and self.command is not None:
            self.command(str(value))

    def _geometry(self):
        width = max(44, self.winfo_width())
        left, right = 22, width - 22
        fraction = (self.get() - self.minimum) / (self.maximum - self.minimum)
        return left, right, left + fraction * (right - left)

    def _set_position(self, x):
        left, right, _ = self._geometry()
        fraction = max(0, min(1, (x - left) / max(1, right - left)))
        self.set(self.minimum + fraction * (self.maximum - self.minimum))

    def _press(self, event):
        if self._state == "disabled":
            return "break"
        self.focus_set()
        _, _, center = self._geometry()
        self._drag_offset = event.x - center if abs(event.x - center) <= 18 else 0
        self._dragging = True
        self.grab_set()
        self._set_position(event.x - self._drag_offset)
        self._start_effect()
        return "break"

    def _drag(self, event):
        if self._dragging and self._state != "disabled":
            self._set_position(event.x - self._drag_offset)
        return "break"

    def _end_drag(self):
        self._dragging = False
        if self.grab_current() is self:
            self.grab_release()

    def _release(self, event):
        if self._dragging:
            self._drag(event)
            self._end_drag()
            self._hovered = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
            self._start_effect()
        return "break"

    def _key(self, event):
        if self._state != "disabled":
            key = event.keysym
            if key in ("Home", "End"):
                self.set(self.minimum if key == "Home" else self.maximum)
            else:
                increment = self.step * (10 if key in ("Prior", "Next") else 1)
                direction = -1 if key in ("Left", "Down", "Next") else 1
                self.set(self.get() + direction * increment)
        return "break"

    def _hover(self, hovered):
        self._hovered = hovered
        self._start_effect()

    def _focus(self, focused):
        self._focused = focused
        if not focused:
            self._end_drag()
        self._start_effect()

    def refresh_theme(self):
        super().configure(bg=self.master.cget("bg"))
        self._surface_cache.clear()
        self._paint()

    def motion_changed(self):
        self._start_effect()

    def _start_effect(self):
        if self._closed:
            return
        self._cancel_effect()
        self._expansion_target = float((self._hovered or self._dragging) and self._state != "disabled")
        self._expansion_from = self._expansion
        self._effect_started = time.perf_counter()
        if self.reduced_motion.get() or self._state == "disabled":
            self._expansion = self._expansion_target
            self._paint()
        else:
            self._animate_effect()

    def _animate_effect(self):
        self._effect_id = None
        if self._closed:
            return
        elapsed = time.perf_counter() - self._effect_started
        self._expansion = self._expansion_from + (self._expansion_target - self._expansion_from) * ease(elapsed / .16)
        self._paint()
        if elapsed < .16 and self.winfo_ismapped():
            self._effect_id = self.after(16, self._animate_effect)

    def _cancel_effect(self):
        if self._effect_id is not None:
            self.after_cancel(self._effect_id)
            self._effect_id = None

    def _unmap(self, event):
        self._end_drag()
        self._hovered = False
        self._cancel_effect()
        self._expansion = 0.0

    def _dispose(self, event):
        if event.widget is self:
            self._closed = True
            self._cancel_effect()
            self.variable.trace_remove("write", self._trace)

    def _paint(self, event=None):
        if self._closed or self._last_value is None:
            return
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 44 or h < 10:
            return
        p = self.theme.palette
        bg = str(self.cget("bg"))
        left, right, center = self._geometry()
        cy = h / 2
        disabled = self._state == "disabled"
        fill = blend(p.SLIDER_TRACK, p.SLIDER_FILL, .25) if disabled else p.SLIDER_FILL
        self.create_line(left, cy, right, cy, fill=p.SLIDER_TRACK, width=7,
                         capstyle=tk.ROUND, tags="slider-track")
        if center > left:
            self.create_line(left, cy, center, cy, fill=fill, width=7,
                             capstyle=tk.ROUND, tags="slider-fill")
        knob_width = 40 + 4 * self._expansion
        knob_height = 32 + 2 * self._expansion
        top = blend(bg, "#ffffff", .45) if disabled else "#ffffff"
        bottom = blend(bg, p.THUMB_BOTTOM, .45) if disabled else p.THUMB_BOTTOM
        self._thumb = frosted_image(self, knob_width, knob_height, 14, top, bottom,
                                    "#ffffff" if not disabled else p.FROST_EDGE, bg, .27)
        self.create_image(center, cy, image=self._thumb, tags="slider-thumb")
        if self._focused:
            rounded_panel(self, 3, 3, w - 3, h - 3, h / 2 - 3, fill="",
                          outline=p.SLIDER_FILL, width=1, tags="focus-ring")
