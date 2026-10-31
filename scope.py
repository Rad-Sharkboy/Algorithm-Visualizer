"""Persistent signal-column scene with interruptible position and color tweens."""

import math

from canvas_items import RetainedCanvas, rounded_points
from motion import lerp_color, ease_out_cubic


class ScopeScreen(RetainedCanvas):
    def __init__(self, parent, theme, manager, reduced_motion):
        super().__init__(parent, theme, manager, role="INSET", height=240)
        self.reduced_motion = reduced_motion
        self.values, self.order, self.display = [], [], {}
        self.targets = {}
        self.domain = (0, 1)
        self._bar_render_keys, self._bar_render_bounds = {}, {}
        self.step_number = 0
        self.progress = 1.0
        self._running = False
        self._scan_present = False
        self._phase = 0.0
        self._wave = {}
        self._hover_index = None
        self._bounds = []
        self._grid = [self.create_line(0, 0, 0, 0) for _ in range(14)]
        self._ticks = [self.create_line(0, 0, 0, 0) for _ in range(8)]
        self._axis = [self.create_text(0, 0, anchor="e", font=(theme.mono, 7)) for _ in range(5)]
        self._baseline = self.create_line(0, 0, 0, 0)
        self._sweep = [self.create_line(0, 0, 0, 0) for _ in range(3)]
        self._readout = self.create_text(0, 0, anchor="ne", font=(theme.mono, 7))
        self._trace_label = self.create_text(0, 0, anchor="nw", text="S I G N A L   /   0 1", font=(theme.mono, 7))
        self.bars = []
        for index in range(64):
            self.bars.append(dict(
                glow=[self.create_polygon(0, 0, 0, 0, 0, 0, fill="", width=2) for _ in range(2)],
                body=self.create_polygon(0, 0, 0, 0, 0, 0, outline=""),
                bands=[self.create_rectangle(0, 0, 0, 0, outline="") for _ in range(8)],
                edge=self.create_line(0, 0, 0, 0, width=1),
                value=self.create_text(0, 0, font=(theme.mono, 8)),
                index=self.create_text(0, 0, font=(theme.mono, 7)),
            ))
        self._tooltip_bg = self.create_rectangle(0, 0, 0, 0, state="hidden", tags="tooltip")
        self._tooltip_text = self.create_text(0, 0, font=(theme.mono, 8), state="hidden", tags="tooltip")
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", self._leave)
        self.bind("<Unmap>", lambda event: self.manager.cancel(self.key + ":scan"))
        self.bind("<Map>", lambda event: self.set_running(self._running))

    def _colors(self, weights, flash):
        p = self.theme.palette
        colors = []
        for suffix in ("", "_MID", "_BASE"):
            channels = [0, 0, 0]
            for role, weight in weights.items():
                if weight < .00001:
                    continue
                color = getattr(p, role + suffix)
                for channel, offset in enumerate((1, 3, 5)):
                    channels[channel] += int(color[offset:offset + 2], 16) * weight
            color = "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in channels))
            colors.append(lerp_color(color, getattr(p, "SETTLED" + suffix), flash * .8))
        return tuple(colors)

    def _roles(self, step):
        return ["SETTLED" if i in step.found or i in step.settled else
                "PIVOT" if i in step.pivot else "COMPARE" if i in step.active else
                "DISCARDED" if i in step.discarded else "BAR" for i in range(len(step.values))]

    def set_step(self, step, number=0, duration=.22, animate=True, reset=False):
        self.manager.cancel(self.key + ":launch")
        self.manager.cancel(self.key + ":wave")
        self._wave.clear()
        values = list(step.values)
        reset = reset or len(values) != len(self.order) or (number == 1 and self.step_number > 1)
        if reset:
            self._scan_present = False
            self.domain = (min([0] + values), max([0] + values))
            self.order = list(range(len(values)))
            self.display = {i: [float(i), float(value), 0.0, {"BAR": 1.0}, 0.0]
                            for i, value in enumerate(values)}
        elif len(step.swap) == 2:
            a, b = step.swap
            self.order[a], self.order[b] = self.order[b], self.order[a]
        self.values, self.step_number = values, number
        self._hover_index = None
        roles = self._roles(step)
        self.targets = {identity: (float(index), float(values[index]), roles[index],
                                  float(roles[index] in ("COMPARE", "PIVOT")), values[index])
                        for index, identity in enumerate(self.order)}
        starts = {identity: [row[0], row[1], row[2], row[3].copy(), row[4]] for identity, row in self.display.items()}
        swapped = set(self.order[i] for i in step.swap) if step.swap else set()
        def update(amount):
            self.progress = amount
            for identity, target in self.targets.items():
                start = starts[identity]
                weights = {role: weight * (1 - amount) for role, weight in start[3].items()}
                weights[target[2]] = weights.get(target[2], 0) + amount
                lift = math.sin(math.pi * amount) if identity in swapped and not self.reduced_motion.get() else 0
                self.display[identity] = [start[0] + (target[0] - start[0]) * amount,
                                          start[1] + (target[1] - start[1]) * amount,
                                          start[2] * (1 - amount) + lift,
                                          weights, start[4] + (target[3] - start[4]) * amount]
            self.paint()
        self.manager.cancel(self.key + ":move")
        if reset:
            update(1)
        else:
            if self.reduced_motion.get() or not animate:
                for identity, target in self.targets.items():
                    starts[identity][0:3] = [target[0], target[1], 0]
                swapped.clear()
                duration = .12
            self.manager.tween(self.key + ":move", duration, update)
        self.paint()

    def settle(self, keep_positions=False):
        self.manager.cancel_prefix(self.key + ":")
        self._wave.clear()
        self.progress = 1.0
        if not keep_positions:
            for identity, target in self.targets.items():
                self.display[identity] = [target[0], target[1], 0, {target[2]: 1.0}, target[3]]
        self.paint()

    def launch(self):
        if self.reduced_motion.get() or not self.values:
            return
        self.manager.cancel(self.key + ":move")
        duration = .38 + .026 * (len(self.values) - 1)
        def update(progress):
            elapsed = progress * duration
            for index, identity in enumerate(self.order):
                target = self.targets[identity]
                growth = ease_out_cubic((elapsed - index * .026) / .38)
                self.display[identity][1] = target[1] * growth
            self.paint()
        self.manager.tween(self.key + ":launch", duration, update, easing=lambda value: value)

    def complete(self, callback):
        self._scan_present = False
        self.set_running(False)
        duration = .18 if self.reduced_motion.get() else .32 + .035 * max(0, len(self.values) - 1)
        def update(progress):
            for index, identity in enumerate(self.order):
                if self.reduced_motion.get():
                    self._wave[identity] = (0, math.sin(math.pi * progress) * .20)
                else:
                    local = max(0, min(1, (progress * duration - index * .035) / .32))
                    self._wave[identity] = (math.sin(math.pi * local) * 8, math.sin(math.pi * local))
            self.paint()
        def finished():
            self._wave.clear()
            self.paint()
            callback()
        self.manager.tween(self.key + ":wave", duration, update, finished, easing=lambda value: value)

    def set_running(self, running):
        self._running = running
        if running:
            self._scan_present = True
        if running and not self.reduced_motion.get() and self.winfo_ismapped():
            self.manager.loop(self.key + ":scan", self._scan)
        else:
            self.manager.cancel(self.key + ":scan")
        self.paint_scan()

    def _scan(self, now, dt):
        self._phase = (self._phase + dt / 10) % 1
        self.paint_scan()

    def _layout(self):
        w, h = self.winfo_width(), self.winfo_height()
        left, right, top, bottom = 45, max(46, w - 22), 54, max(72, h - 36)
        low, high = self.domain
        if low == high:
            high = low + 1
        span = high - low
        return left, right, top, bottom, low, high, span

    def paint_scan(self):
        if self._closed:
            return
        p = self.theme.palette
        left, right, top, bottom, *_ = self._layout()
        x = left + (right - left) * self._phase
        for offset, item in enumerate(self._sweep):
            self.position(item, x - offset * 2, top, x - offset * 2, bottom)
            self.style(item, fill=lerp_color(p.INSET, p.BAR, .12 - offset * .03),
                       state="normal" if self._scan_present and not self.reduced_motion.get() else "hidden")
        self.position(self._readout, self.winfo_width() - 20, 14)
        self.style(self._readout, text=f"STEP {self.step_number:04d} / {min(99, round(self.manager.fps)):02d} FPS", fill=p.MUTED)

    def paint(self):
        if self._closed or self.winfo_width() < 50:
            return
        p = self.theme.palette
        left, right, top, bottom, low, high, span = self._layout()
        def y(value):
            return top + (high - value) / span * (bottom - top)
        grid = lerp_color(p.INSET, p.BORDER, .62)
        for index in range(5):
            yy = top + (bottom - top) * index / 4
            self.position(self._grid[index], left, yy, right, yy)
            self.style(self._grid[index], fill=grid, dash=(1, 5))
            self.position(self._axis[index], left - 12, yy)
            self.style(self._axis[index], text=str(round(high - span * index / 4)), fill=p.MUTED)
        for index in range(9):
            xx = left + (right - left) * index / 8
            self.position(self._grid[index + 5], xx, top, xx, bottom)
            self.style(self._grid[index + 5], fill=grid, dash=(1, 7))
        for index, (xx, yy, sx, sy) in enumerate(((left, top, 1, 1), (right, top, -1, 1),
                                                 (left, bottom, 1, -1), (right, bottom, -1, -1))):
            self.position(self._ticks[index * 2], xx, yy, xx + sx * 10, yy)
            self.position(self._ticks[index * 2 + 1], xx, yy, xx, yy + sy * 10)
            self.style(self._ticks[index * 2], fill=p.MUTED)
            self.style(self._ticks[index * 2 + 1], fill=p.MUTED)
        baseline = y(0)
        self.position(self._baseline, left, baseline, right, baseline)
        self.style(self._baseline, fill=lerp_color(p.BORDER, p.MUTED, .25))
        self.position(self._trace_label, left, 14)
        self.style(self._trace_label, fill=p.MUTED)
        self.paint_scan()
        self._bounds = []
        count = len(self.values)
        stride = (right - left) / max(1, count)
        gap = max(3, min(12, stride * .28))
        inverse = {identity: index for index, identity in enumerate(self.order)}
        state_colors = {}
        for identity, items in enumerate(self.bars):
            all_items = items["glow"] + [items["body"]] + items["bands"] + [items["edge"], items["value"], items["index"]]
            if identity not in self.display or identity not in inverse:
                if self._bar_render_keys.get(identity) != "hidden":
                    for item in all_items:
                        self.style(item, state="hidden")
                    self._bar_render_keys[identity] = "hidden"
                continue
            index = inverse[identity]
            slot, value, lift, weights, emphasis = self.display[identity]
            wave_lift, flash = self._wave.get(identity, (0, 0))
            state = (tuple(weights.items()), flash)
            if state not in state_colors:
                state_colors[state] = self._colors(weights, flash)
            colors = state_colors[state]
            color = colors[0]
            signature = (index, slot, value, lift, colors, emphasis, wave_lift, self.values[index], count,
                         left, right, top, bottom, low, high, p.MUTED, p.TEXT, p.INSET)
            if self._bar_render_keys.get(identity) == signature:
                self._bounds.append(self._bar_render_bounds[identity])
                continue
            self._bar_render_keys[identity] = signature
            x0, x1 = left + slot * stride + gap / 2, left + (slot + 1) * stride - gap / 2
            y0, y1 = sorted((baseline, y(value)))
            y0 = min(y0, y1 - 3)
            y0, y1 = y0 - lift * 16 - wave_lift, y1 - lift * 16 - wave_lift
            radius = min(5, (x1 - x0) / 3, (y1 - y0) / 2)
            for glow_index, item in enumerate(items["glow"]):
                pad = 5 - glow_index * 2
                self.position(item, *rounded_points(x0 - pad, y0 - pad, x1 + pad, y1 + pad, radius + pad))
                self.style(item, outline=lerp_color(p.INSET, color, emphasis * (.11 + glow_index * .1)),
                           state="normal" if emphasis > .01 else "hidden")
            self.position(items["body"], *rounded_points(x0, y0, x1, y1, radius))
            self.style(items["body"], fill=color, state="normal")
            band_top = y0 + radius
            gradient_top = lerp_color(p.INSET, color, .94)
            for band, item in enumerate(items["bands"]):
                self.position(item, x0, band_top + (y1 - band_top) * band / 8,
                              x1, band_top + (y1 - band_top) * (band + 1) / 8)
                amount = band / 7
                shade = (lerp_color(gradient_top, colors[1], amount * 2) if amount <= .5 else
                         lerp_color(colors[1], colors[2], amount * 2 - 1))
                self.style(item, fill=shade, state="normal")
            self.position(items["edge"], x0 + radius, y0 + .6, x1 - radius, y0 + .6)
            self.style(items["edge"], fill=lerp_color(color, p.TEXT, .30), state="normal")
            show = stride >= 23 or emphasis > .5
            self.position(items["value"], (x0 + x1) / 2, y0 - 12 if value >= 0 else y1 + 12)
            self.style(items["value"], text=str(self.values[index]), fill=lerp_color(p.MUTED, p.TEXT, emphasis),
                       state="normal" if show else "hidden")
            self.position(items["index"], left + (index + .5) * stride, self.winfo_height() - 13)
            self.style(items["index"], text=f"{index:02}", fill=p.MUTED,
                       state="normal" if count <= 32 or index % 5 == 0 else "hidden")
            self._bar_render_bounds[identity] = (x0, x1, index, self.values[index])
            self._bounds.append(self._bar_render_bounds[identity])
        self._paint_tooltip()

    def _hover(self, event):
        self._hover_index = next((index for x0, x1, index, _ in self._bounds if x0 <= event.x <= x1), None)
        self._paint_tooltip()

    def _leave(self, event=None):
        self._hover_index = None
        self._paint_tooltip()

    def _paint_tooltip(self):
        p = self.theme.palette
        index = self._hover_index
        visible = index is not None and index < len(self.values)
        for item in (self._tooltip_bg, self._tooltip_text):
            self.style(item, state="normal" if visible else "hidden")
        if visible:
            cx = self.winfo_width() / 2
            self.position(self._tooltip_bg, cx - 100, 4, cx + 100, 28)
            self.style(self._tooltip_bg, fill=p.PANEL, outline=p.BORDER)
            self.position(self._tooltip_text, cx, 16)
            self.style(self._tooltip_text, text=f"INDEX {index:02} / VALUE {self.values[index]}", fill=p.TEXT)
