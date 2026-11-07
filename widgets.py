"""Flat instrument controls with retained items and a shared animation clock."""

import math
import tkinter as tk

from canvas_items import RetainedCanvas
from layout import LayoutEntry
from motion import lerp_color


class AnimatedButton(RetainedCanvas):
    def __init__(self, parent, theme, manager, reduced_motion, command, text="", icon=None,
                 primary=False, width=106, height=40, role="BG"):
        super().__init__(parent, theme, manager, role=role, width=width, height=height, takefocus=True, cursor="hand2")
        self.reduced_motion, self.command = reduced_motion, command
        self._text, self.icon, self.primary = text, icon, primary
        self._state = "normal"
        self._hovered = self._pressed = self._focused = self.selected = False
        self._hover_amount = self._press_amount = self._icon = 0.0
        self._icon_target = 0.0
        self._playback = "ready"
        self._surface = self.create_image(0, 0, anchor="nw")
        self._surface_image = None
        self._label = self.create_text(0, 0, font=theme.typeface(11 if primary else 10, bold=primary))
        self._polygons = [self.create_polygon(0, 0, 0, 0, 0, 0, outline="", state="hidden") for _ in range(2)]
        self._lines = [self.create_line(0, 0, 0, 0, width=1.4, state="hidden") for _ in range(4)]
        self._arc = self.create_arc(0, 0, 0, 0, style="arc", width=1.4, start=40, extent=280, state="hidden")
        self.bind("<Enter>", lambda event: self._hover(True))
        self.bind("<Leave>", lambda event: self._hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda event: self._focus(True))
        self.bind("<FocusOut>", lambda event: self._focus(False))
        for key in ("space", "Return"):
            self.bind(f"<KeyPress-{key}>", self._key_press)
            self.bind(f"<KeyRelease-{key}>", self._key_release)
        self.bind("<Unmap>", lambda event: self.settle())

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        changed = handled = False
        for name in ("text", "state", "command", "selected"):
            if name in kwargs:
                handled = True
                value = kwargs.pop(name)
                attribute = {"text": "_text", "state": "_state"}.get(name, name)
                if getattr(self, attribute) != value:
                    setattr(self, attribute, value)
                    changed = True
        result = super().configure(cnf, **kwargs) if cnf is not None or kwargs or not handled else None
        if changed:
            if self._state == "disabled":
                self._pressed = False
            self._animate()
        return result

    config = configure

    def cget(self, key):
        if key in ("text", "state"):
            return getattr(self, "_" + key)
        return super().cget(key)

    def invoke(self):
        if not self._closed and self._state != "disabled":
            return self.command()

    def set_playback(self, state):
        target = 1.0 if state == "running" else 0.0
        text = {"running": "Pause", "paused": "Resume", "done": "Replay"}.get(state, "Run")
        changed = state != self._playback
        self._playback, self._text, self._icon_target = state, text, target
        if changed:
            self._animate()
        else:
            self.paint()

    def _hover(self, value):
        self._hovered = value
        self._animate()

    def _focus(self, value):
        self._focused = value
        if not value:
            self._pressed = False
        self._animate()

    def _press(self, event):
        if self._state != "disabled":
            self.focus_set()
            self._pressed = True
            self._animate()

    def _release(self, event):
        armed, self._pressed = self._pressed, False
        if armed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()
        self._animate()

    def _key_press(self, event):
        self._press(event)
        return "break"

    def _key_release(self, event):
        armed, self._pressed = self._pressed, False
        if armed:
            self.invoke()
        self._animate()
        return "break"

    def _animate(self):
        if self._closed:
            return
        start = self._hover_amount, self._press_amount, self._icon
        target = float(self._hovered or self._focused), float(self._pressed), self._icon_target
        def update(amount):
            self._hover_amount, self._press_amount, self._icon = [a + (b - a) * amount for a, b in zip(start, target)]
            self.paint()
        self.manager.cancel(self.key + ":control")
        if self.reduced_motion.get() or self._state == "disabled":
            update(1)
        else:
            self.manager.tween(self.key + ":control", .12, update)

    def settle(self):
        self.manager.cancel_prefix(self.key + ":")
        self._hover_amount = float(self._hovered or self._focused)
        self._press_amount = float(self._pressed)
        self._icon = self._icon_target
        self.paint()

    def motion_changed(self):
        self.settle()

    def _surface_sprite(self, surface):
        w, h = self.winfo_width(), self.winfo_height()
        hover = round(self._hover_amount * 6) / 6
        press = round(self._press_amount * 6) / 6
        inset = 2 + press * 2
        bg = getattr(surface, self.bg_role)
        top = surface.BUTTON_TOP if self.primary else bg
        bottom = surface.BUTTON_BASE if self.primary else bg
        if self.primary:
            top = lerp_color(lerp_color(top, surface.TEXT, hover * .1), surface.BG, press * .2)
            bottom = lerp_color(lerp_color(bottom, surface.TEXT, hover * .1), surface.BG, press * .2)
        border = surface.ACCENT if self.primary or self.selected or self._focused else lerp_color(surface.BORDER, surface.ACCENT, hover)
        if self._state == "disabled":
            border, top, bottom = surface.BORDER, bg, bg
        image = self.theme.sprites.box(
            max(1, self.theme.px(w - 2 * inset)), max(1, self.theme.px(h - 2 * inset)),
            self.theme.px(5), top, border=border, border_w=self.theme.scale * (2 if self._focused else 1),
            fill_bottom=bottom)
        return inset, image

    def prepare_palette(self, palette):
        if not self._closed and self.winfo_width() >= 10 and self.winfo_height() >= 10:
            self._surface_sprite(palette)

    def paint(self):
        if self._closed or not hasattr(self, "_surface"):
            return
        p = self.theme.palette
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        color = p.ON_ACCENT if self.primary else lerp_color(p.TEXT, p.ACCENT, self._hover_amount)
        if self._state == "disabled":
            color = p.MUTED
        if self.selected:
            color = p.ACCENT
        inset, self._surface_image = self._surface_sprite(self.theme.control_palette)
        self.position(self._surface, inset, inset)
        self.style(self._surface, image=self._surface_image)
        self.position(self._label, w / 2 + (10 if self.icon else 0), h / 2 + self._press_amount)
        self.style(self._label, text=self._text.upper(), fill=color)
        x, y = 20, h / 2 + self._press_amount
        if self.icon in ("play", "step"):
            play = ((-4, -6, 1, -3, 1, 3, -4, 6), (1, -3, 7, 0, 7, 0, 1, 3))
            pause = ((-5, -6, -2, -6, -2, 6, -5, 6), (3, -6, 6, -6, 6, 6, 3, 6))
            amount = self._icon if self.icon == "play" else 0
            for item, start, end in zip(self._polygons, play, pause):
                points = [a + (b - a) * amount + (x if i % 2 == 0 else y) for i, (a, b) in enumerate(zip(start, end))]
                self.position(item, *points)
                self.style(item, fill=color, state="normal")
            if self.icon == "step":
                self.position(self._lines[0], x + 9, y - 6, x + 9, y + 6)
                self.style(self._lines[0], fill=color, state="normal")
        elif self.icon == "stop":
            self.position(self._polygons[0], x - 5, y - 5, x + 5, y - 5, x + 5, y + 5, x - 5, y + 5)
            self.style(self._polygons[0], fill=color, state="normal")
        elif self.icon in ("reset", "generate"):
            self.position(self._arc, x - 6, y - 6, x + 6, y + 6)
            self.style(self._arc, outline=color, state="normal")
            self.position(self._polygons[0], x + 5, y - 7, x + 7, y - 1, x + 1, y - 4)
            self.style(self._polygons[0], fill=color, state="normal")
        elif self.icon == "toggle":
            self.position(self._polygons[0], x - 5, y - 5, x + 5, y - 5, x + 5, y + 5, x - 5, y + 5)
            self.style(self._polygons[0], fill=color if self.selected else "", outline=color, state="normal")
        elif self.icon == "guide":
            self.position(self._lines[0], x - 5, y - 6, x + 5, y - 6, x + 5, y + 6, x - 5, y + 6, x - 5, y - 6)
            self.position(self._lines[1], x - 2, y - 2, x + 2, y - 2)
            self.position(self._lines[2], x - 2, y + 2, x + 2, y + 2)
            for item in self._lines[:3]:
                self.style(item, fill=color, state="normal")


class MotionToggle(AnimatedButton):
    def __init__(self, parent, theme, manager, variable, command):
        self.variable, self.on_change = variable, command
        super().__init__(parent, theme, manager, variable, self._toggle, text="Reduced motion", icon="toggle", width=180, height=36)
        self.selected = variable.get()
        self._trace = variable.trace_add("write", self._changed)

    def _changed(self, *args):
        self.selected = self.variable.get()
        self._animate()

    def _toggle(self):
        self.variable.set(not self.variable.get())
        self.on_change()

    def _dispose(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)
        super()._dispose(event)


class InstrumentSlider(RetainedCanvas):
    def __init__(self, parent, theme, manager, variable, command, reduced_motion,
                 from_=0, to=100, length=170, step=1, role="BG"):
        super().__init__(parent, theme, manager, role=role, width=length, height=32, takefocus=True, cursor="hand2")
        self.variable, self.command, self.reduced_motion = variable, command, reduced_motion
        self.minimum, self.maximum, self.step = float(from_), float(to), float(step)
        self._state = "normal"
        self._dragging = self._focused = self._hovered = self._syncing = False
        self._last_value = None
        self.visual = 0.0
        self._handle_amount = 0.0
        self._drag_offset = 0
        self._track = self.create_line(0, 0, 0, 0, width=4, capstyle="round")
        self._fill = self.create_line(0, 0, 0, 0, width=4, capstyle="round")
        self._thumb = self.create_image(0, 0)
        self._thumb_image = None
        self._trace = variable.trace_add("write", self._changed)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda event: self._focus(True))
        self.bind("<FocusOut>", lambda event: self._focus(False))
        self.bind("<Unmap>", lambda event: self._unmap())
        self.bind("<Enter>", lambda event: self._hover(True))
        self.bind("<Leave>", lambda event: self._hover(False))
        for key in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
            self.bind(f"<KeyPress-{key}>", self._key)
        self.bind("<KeyPress-space>", lambda event: "break")
        self._changed()
        self.visual = self.get()

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        state = kwargs.pop("state", None)
        if state is not None:
            self._state = state
            if state == "disabled":
                self._unmap()
        result = super().configure(cnf, **kwargs) if cnf is not None or kwargs or state is None else None
        if state is not None:
            self.paint()
        return result

    config = configure

    def cget(self, key):
        return self._state if key == "state" else super().cget(key)

    def get(self):
        return self._last_value

    def set(self, value):
        self.variable.set(value)

    def _changed(self, *args):
        if self._closed or self._syncing:
            return
        invalid = False
        try:
            raw = float(self.variable.get())
            if not math.isfinite(raw):
                invalid, raw = True, self.minimum
        except (ValueError, tk.TclError):
            invalid, raw = True, self.minimum
        value = max(self.minimum, min(self.maximum, self.minimum + round((raw - self.minimum) / self.step) * self.step))
        if invalid or value != raw:
            self._syncing = True
            try:
                self.variable.set(value)
            finally:
                self._syncing = False
        changed = value != self._last_value
        self._last_value = value
        start = self.visual
        def update(amount):
            self.visual = start + (value - start) * amount
            self.paint()
        if self.reduced_motion.get() or not self.winfo_ismapped():
            self.manager.cancel(self.key + ":thumb")
            update(1)
        else:
            self.manager.tween(self.key + ":thumb", .11, update)
        if changed and self.command is not None:
            self.command(str(value))

    def _geometry(self):
        left, right = 12, max(13, self.winfo_width() - 12)
        return left, right, left + (right - left) * (self.visual - self.minimum) / (self.maximum - self.minimum)

    def _set_position(self, x):
        left, right, _ = self._geometry()
        self.set(self.minimum + max(0, min(1, (x - left) / (right - left))) * (self.maximum - self.minimum))

    def _press(self, event):
        if self._state != "disabled":
            self.focus_set()
            _, _, center = self._geometry()
            self._drag_offset = event.x - center if abs(event.x - center) < 10 else 0
            self._dragging = True
            self.grab_set()
            self._set_position(event.x - self._drag_offset)
            self._animate_handle()
        return "break"

    def _drag(self, event):
        if self._dragging and self._state != "disabled":
            self._set_position(event.x - self._drag_offset)
        return "break"

    def _release(self, event):
        if self._dragging:
            self._drag(event)
            self._end_drag()
        return "break"

    def _end_drag(self):
        self._dragging = False
        if self.grab_current() is self:
            self.grab_release()
        self._animate_handle()

    def _focus(self, value):
        self._focused = value
        if not value:
            self._end_drag()
        self._animate_handle()

    def _hover(self, value):
        self._hovered = value
        self._animate_handle()

    def _animate_handle(self):
        if self._closed:
            return
        start = self._handle_amount
        target = float(self._focused or self._hovered or self._dragging)
        def update(amount):
            self._handle_amount = start + (target - start) * amount
            self.paint()
        self.manager.cancel(self.key + ":handle")
        if self.reduced_motion.get() or not self.winfo_ismapped():
            update(1)
        else:
            self.manager.tween(self.key + ":handle", .12, update)

    def _key(self, event):
        if self._state != "disabled":
            if event.keysym in ("Home", "End"):
                self.set(self.minimum if event.keysym == "Home" else self.maximum)
            else:
                sign = -1 if event.keysym in ("Left", "Down", "Next") else 1
                self.set(self.get() + sign * self.step * (10 if event.keysym in ("Prior", "Next") else 1))
        return "break"

    def _unmap(self):
        self._end_drag()
        self.motion_changed()

    def motion_changed(self):
        self.manager.cancel_prefix(self.key + ":")
        self.visual = self.get()
        self._handle_amount = float(self._focused or self._hovered or self._dragging)
        self.paint()

    def _dispose(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)
        super()._dispose(event)

    def _thumb_sprite(self, surface):
        amount = round(self._handle_amount * 6) / 6
        diameter = self.theme.px(22 + 2 * amount)
        fill = surface.THUMB if self._state != "disabled" else lerp_color(surface.THUMB, surface.PANEL, .5)
        edge = lerp_color(surface.MUTED, surface.ACCENT, amount)
        return self.theme.sprites.box(
            diameter, diameter, diameter / 2, fill, border=edge,
            border_w=self.theme.scale * (1 + amount), fill_bottom=lerp_color(fill, surface.BG, .08),
            shadow=.16, shadow_dy=self.theme.scale, shadow_blur=self.theme.scale)

    def prepare_palette(self, palette):
        if not self._closed:
            self._thumb_sprite(palette)

    def paint(self):
        if self._closed or not hasattr(self, "_thumb") or self._last_value is None:
            return
        p = self.theme.palette
        left, right, center = self._geometry()
        cy = 16
        color = p.MUTED if self._state == "disabled" else p.ACCENT
        self.position(self._track, left, cy, right, cy)
        self.style(self._track, fill=p.BORDER)
        self.position(self._fill, left, cy, center, cy)
        self.style(self._fill, fill=color)
        self._thumb_image = self._thumb_sprite(self.theme.control_palette)
        self.position(self._thumb, center, cy)
        self.style(self._thumb, image=self._thumb_image)


class InstrumentEntry(LayoutEntry):
    def __init__(self, parent, theme, manager, reduced_motion, **kwargs):
        super().__init__(parent, theme, relief="flat", bd=0, highlightthickness=1, font=theme.typeface(10), **kwargs)
        self.theme, self.manager, self.reduced_motion = theme, manager, reduced_motion
        self.key = f"entry:{self}"
        self._focus_amount = 0.0
        theme.bind(self, bg="INSET", fg="TEXT", insertbackground="ACCENT", disabledbackground="INSET",
                   disabledforeground="MUTED", selectbackground="BORDER", selectforeground="TEXT")
        theme.register(self)
        self.bind("<FocusIn>", lambda event: self._focus(True))
        self.bind("<FocusOut>", lambda event: self._focus(False))
        self.bind("<Destroy>", lambda event: manager.cancel(self.key))
        self.refresh_theme()

    def _focus(self, value):
        start = self._focus_amount
        def update(amount):
            self._focus_amount = start + (float(value) - start) * amount
            self.refresh_theme()
        if self.reduced_motion.get():
            self.manager.cancel(self.key)
            update(1)
        else:
            self.manager.tween(self.key, .12, update)

    def refresh_theme(self):
        p = self.theme.palette
        color = lerp_color(p.BORDER, p.ACCENT, self._focus_amount)
        self.configure(highlightbackground=color, highlightcolor=color)


class InstrumentSelect(AnimatedButton):
    def __init__(self, parent, theme, manager, reduced_motion, variable, values, width=160, labels=None, role="BG"):
        self.variable, self.values = variable, tuple(values)
        self.labels = labels or {}
        self.popup = None
        self._popup_canvas = None
        self._popup_owner = None
        self._popup_configure = None
        super().__init__(parent, theme, manager, reduced_motion, self._open, width=width, height=34, role=role)
        self._chevron = self.create_line(0, 0, 0, 0, 0, 0, width=1)
        self._trace = variable.trace_add("write", self._value_changed)
        self.bind("<KeyPress-Down>", self._open_key)
        self.bind("<KeyPress-Up>", self._open_key)
        self.bind("<Unmap>", self._unmap)
        self._value_changed()

    def _value_changed(self, *args):
        self._text = self.labels.get(self.variable.get(), self.variable.get())
        self.paint()

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

    def _open_key(self, event):
        self._open()
        return "break"

    def _open(self):
        if self._state == "disabled" or self._closed or not self.winfo_ismapped():
            return
        if self.popup is not None:
            self._close_popup()
            return
        root = self.winfo_toplevel()
        previous = getattr(root, "_instrument_select", None)
        if previous is not None and previous is not self:
            previous._close_popup(restore_focus=False)
        root._instrument_select = self
        self._popup_owner = root
        self.popup = self.theme.frame(root, role="INSET")
        self.popup.bind("<Destroy>", self._popup_destroyed)
        self._popup_font = self.theme.typeface(10)
        self._row_height = max(32, math.ceil(self._popup_font.metrics("linespace") / self.theme.scale) + 14)
        width = max(self._popup_font.measure(self.labels.get(value, value).upper()) for value in self.values) / self.theme.scale + 34
        self._popup_width = max(self.winfo_width(), 164, width)
        self._popup_height = len(self.values) * self._row_height + 4
        w, h = self._popup_width, self._popup_height
        canvas = RetainedCanvas(self.popup, self.theme, self.manager, role="INSET", width=w, height=h, takefocus=True)
        canvas.pack(fill="both", expand=True)
        self._popup_canvas = canvas
        self._choice = self.values.index(self.variable.get()) if self.variable.get() in self.values else 0
        self._popup_border = canvas.create_rectangle(1, 1, w - 1, h - 1, fill="", width=1)
        self._popup_mark = canvas.create_line(4, 0, 4, 0, width=2)
        self._popup_text = [canvas.create_text(16, 2 + (i + .5) * self._row_height, anchor="w",
                                             font=self._popup_font) for i in range(len(self.values))]
        canvas.paint = self._paint_popup
        self._paint_popup()
        canvas.bind("<Map>", self._activate_popup)
        canvas.bind("<FocusOut>", self._popup_focus_out)
        canvas.bind("<Motion>", self._popup_hover)
        canvas.bind("<ButtonPress-1>", self._popup_click)
        canvas.bind("<KeyPress>", lambda event: "break")
        canvas.bind("<KeyPress-Up>", lambda event: self._popup_key(-1))
        canvas.bind("<KeyPress-Down>", lambda event: self._popup_key(1))
        canvas.bind("<KeyPress-Return>", lambda event: self._choose())
        canvas.bind("<KeyPress-space>", lambda event: self._choose())
        canvas.bind("<KeyPress-Escape>", lambda event: self._close_popup())
        canvas.bind("<KeyPress-Tab>", self._popup_tab)
        canvas.bind("<KeyPress-ISO_Left_Tab>", lambda event: self._popup_tab(event, backwards=True))
        canvas.bind("<Shift-KeyPress-Tab>", lambda event: self._popup_tab(event, backwards=True))
        self._popup_configure = root.bind("<Configure>", self._popup_reposition, add="+")
        self._place_popup()
        self.popup.lift()

    def _place_popup(self):
        root = self._popup_owner
        if self.popup is None or root is None:
            return
        scale = self.theme.scale
        root_width, root_height = root.winfo_width() / scale, root.winfo_height() / scale
        width = min(self._popup_width, root_width)
        height = min(self._popup_height, root_height)
        x = (self.winfo_rootx() - root.winfo_rootx()) / scale
        y = (self.winfo_rooty() - root.winfo_rooty()) / scale + self.winfo_height()
        if y + height > root_height:
            y = (self.winfo_rooty() - root.winfo_rooty()) / scale - height
        x = max(0, min(x, root_width - width))
        y = max(0, min(y, root_height - height))
        self.popup.place(x=x, y=y, width=width, height=height)

    def _popup_reposition(self, event):
        if event.widget is self._popup_owner:
            self._place_popup()

    def _activate_popup(self, event):
        canvas = self._popup_canvas
        if self.popup is None or event.widget is not canvas or not canvas.winfo_ismapped():
            return
        canvas.grab_set()
        canvas.focus_set()

    def _popup_focus_out(self, event):
        def check_focus():
            canvas = self._popup_canvas
            if canvas is not None and canvas.focus_displayof() is not canvas:
                self._close_popup(restore_focus=False)
        if not self._closed and self.popup is not None:
            self.manager.call_later(0, check_focus, key=self.key + ":popup-focus")

    def _popup_tab(self, event, backwards=False):
        destination = self.tk_focusPrev() if backwards else self.tk_focusNext()
        self._close_popup(restore_focus=False)
        if destination is not None:
            destination.focus_set()
        return "break"

    def _paint_popup(self):
        if self.popup is None:
            return
        c, p = self._popup_canvas, self.theme.palette
        c.position(self._popup_border, 1, 1, max(1, c.winfo_width() - 1), max(1, c.winfo_height() - 1))
        c.style(self._popup_border, outline=p.BORDER)
        c.position(self._popup_mark, 4, self._choice * self._row_height + 8,
                   4, (self._choice + 1) * self._row_height - 5)
        c.style(self._popup_mark, fill=p.ACCENT)
        for index, (item, value) in enumerate(zip(self._popup_text, self.values)):
            c.style(item, text=self.labels.get(value, value).upper(), fill=p.ACCENT if index == self._choice else p.TEXT)

    def _popup_key(self, direction):
        self._choice = max(0, min(len(self.values) - 1, self._choice + direction))
        self._paint_popup()
        return "break"

    def _popup_hover(self, event):
        row = int((event.y - 2) // self._row_height)
        if 0 <= row < len(self.values):
            self._choice = row
            self._paint_popup()

    def _popup_click(self, event):
        if not 0 <= event.x < self._popup_canvas.winfo_width() or not 0 <= event.y < self._popup_canvas.winfo_height():
            return self._close_popup()
        self._choice = min(len(self.values) - 1, max(0, int((event.y - 2) // self._row_height)))
        return self._choose()

    def _choose(self):
        if self.popup is None:
            return "break"
        value = self.values[self._choice]
        self._close_popup()
        self.variable.set(value)
        self.event_generate("<<ComboboxSelected>>")
        return "break"

    def _close_popup(self, restore_focus=True):
        if self.popup is not None:
            popup, canvas = self.popup, self._popup_canvas
            self.popup = self._popup_canvas = None
            self.manager.cancel(self.key + ":popup-focus")
            if canvas is not None and canvas.winfo_exists() and canvas.grab_current() is canvas:
                canvas.grab_release()
            self._release_popup_owner()
            popup.destroy()
            if restore_focus and not self._closed and self.winfo_exists() and self.winfo_ismapped():
                self.focus_set()
        return "break"

    def _popup_destroyed(self, event):
        if event.widget is self.popup:
            self.popup = self._popup_canvas = None
            self.manager.cancel(self.key + ":popup-focus")
            self._release_popup_owner()

    def _release_popup_owner(self):
        owner, binding = self._popup_owner, self._popup_configure
        self._popup_owner = self._popup_configure = None
        if owner is not None:
            if getattr(owner, "_instrument_select", None) is self:
                owner._instrument_select = None
            if binding is not None and owner.winfo_exists():
                owner.unbind("<Configure>", binding)

    def _unmap(self, event):
        self._close_popup(restore_focus=False)
        self.settle()

    def _dispose(self, event):
        if event.widget is self:
            self._close_popup()
            self.variable.trace_remove("write", self._trace)
        super()._dispose(event)

    def paint(self):
        super().paint()
        if self._closed or not hasattr(self, "_chevron"):
            return
        w, h = self.winfo_width(), self.winfo_height()
        self.position(self._label, (w - 16) / 2, h / 2)
        self.position(self._chevron, w - 19, h / 2 - 2, w - 15, h / 2 + 2, w - 11, h / 2 - 2)
        self.style(self._chevron, fill=self.theme.palette.MUTED)
