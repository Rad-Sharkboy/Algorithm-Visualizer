"""Algo Studio: a retained-mode Tkinter algorithm instrument."""

import itertools
import time
import tkinter as tk
import webbrowser

from algorithms import ALGORITHMS, Step
from datasets import generate_values, parse_values
from motion import AnimationManager
from theme import StudioTheme, SPACING, THEME_LABELS
from preferences import load_theme, save_theme
from scope import ScopeScreen
from panels import DisplayTitle, MeterRow, StatusLamp, Navigation
from widgets import AnimatedButton, InstrumentSlider, InstrumentSelect, InstrumentEntry, MotionToggle


class Visualizer:
    def __init__(self, root):
        self.root = root
        self.manager = AnimationManager(root)
        self.reduced_motion = tk.BooleanVar(value=False)
        self._saved_theme = load_theme(THEME_LABELS)
        self.theme = StudioTheme(root, self.manager, self.reduced_motion, mode=self._saved_theme)
        self.font = self.mono = self.theme.mono
        self.theme.bind(root, bg="BG")
        self.theme_var = tk.StringVar(value=self._saved_theme)
        self._theme_id = None
        root.title("Algo Studio · Algorithm Visualizer")
        root.geometry(f"{min(1280, max(1000, root.winfo_screenwidth() - 60))}x"
                      f"{min(900, max(740, root.winfo_screenheight() - 60))}")
        root.minsize(1000, 740)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._closed = False
        self._after_id = None
        self._motion_id = None
        self._motion_progress = self._finish_progress = 1.0
        self._previous_step = None
        self._iterator = None
        self.state = "ready"
        self.comparisons = self.writes = self.steps = 0
        self.elapsed = 0.0
        self._active_since = None
        self._completing = False
        self._launch_id = None
        self.category = "Sort"
        self.algorithm = "Merge Sort"
        self.original, self.arr = [], []
        self.current = Step((), "Choose an algorithm, then press Run.")
        self.size_var = tk.DoubleVar(value=28)
        self.speed_var = tk.DoubleVar(value=32)
        self.target_var = tk.StringVar(value="50")
        self.preset_var = tk.StringVar(value="Random")
        self.custom_var = tk.StringVar()
        self._build_sidebar()
        self._build_main()
        self._select_algorithm(self.algorithm)
        self.new_array()
        root.bind("<space>", self._space)
        root.bind("<Escape>", lambda event: self.stop())
        root.bind("<Control-r>", lambda event: self.reset())
        root.bind("<Right>", self._right)
        root.bind("<Configure>", self._resize)
        self._theme_id = self.manager.call_later(2000, self._poll_theme)
        self._launch_id = self.manager.call_later(80, self._launch)

    @property
    def palette(self):
        return self.theme.palette

    @property
    def _motion_progress(self):
        return self.canvas.progress if hasattr(self, "canvas") else 1.0

    @_motion_progress.setter
    def _motion_progress(self, value):
        if hasattr(self, "canvas"):
            self.canvas.progress = value

    def _label(self, parent, text="", size=9, role="TEXT", bg="BG", **kwargs):
        return self.theme.label(parent, text, size, role, bg, **kwargs)

    def _button(self, parent, text, command, icon=None, width=100, primary=False, role="BG", height=40):
        return AnimatedButton(parent, self.theme, self.manager, self.reduced_motion, command,
                              text=text, icon=icon, width=width, primary=primary, role=role, height=height)

    def _change_theme(self, event=None):
        mode = self.theme_var.get()
        self.theme.select(mode)
        if mode != self._saved_theme:
            if save_theme(mode, THEME_LABELS):
                self._saved_theme = mode

    def _poll_theme(self):
        self._theme_id = None
        if self._closed:
            return
        if self.theme_var.get() == "System":
            self.theme.select("System")
        self._theme_id = self.manager.call_later(2000, self._poll_theme)

    def _build_sidebar(self):
        rail = self.theme.frame(self.root, width=SPACING["sidebar"])
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        self.sidebar = rail
        self.theme.frame(self.root, role="BORDER", width=1).pack(side="left", fill="y")
        brand = self.theme.frame(rail)
        brand.pack(fill="x", padx=22, pady=(29, 0))
        self._label(brand, "A L G O", 14, bold=True).pack(anchor="w")
        self._label(brand, "S T U D I O", 9, "MUTED").pack(anchor="w", pady=(3, 18))
        self.theme.frame(rail, role="BORDER", height=1).pack(fill="x", padx=22)
        self._label(rail, "I N S T R U M E N T  /  0 1", 7, "MUTED").pack(anchor="w", padx=22, pady=(14, 25))
        self._label(rail, "A L G O R I T H M S", 8, "MUTED").pack(anchor="w", padx=22, pady=(0, 10))
        tabs = self.theme.frame(rail)
        tabs.pack(fill="x", padx=18)
        self.tab_buttons = {}
        for category in ("Sort", "Search"):
            button = self._button(tabs, category, lambda c=category: self._set_category(c), width=82, height=32)
            button.pack(side="left", fill="x", expand=True)
            self.tab_buttons[category] = button
        self.algorithm_list = Navigation(rail, self.theme, self.manager, self.reduced_motion, self._select_algorithm)
        self.algorithm_list.pack(fill="x", padx=16, pady=(13, 6))
        self.nav_buttons = {}
        footer = self.theme.frame(rail)
        footer.pack(side="bottom", fill="x", padx=17, pady=18)
        self._label(footer, "O P E R A T I O N", 7, "MUTED").pack(anchor="w", padx=5)
        self._label(footer, "SPACE   Run / pause\nRIGHT   Single step\nESC     Stop\nCTRL R  Reset", 8,
                    "MUTED", justify="left", anchor="w").pack(anchor="w", padx=5, pady=(10, 14))
        self.motion_toggle = MotionToggle(footer, self.theme, self.manager, self.reduced_motion, self._motion_preference_changed)
        self.motion_toggle.pack(fill="x")
        self.library_count = self._label(footer, "13 algorithms", 7, "MUTED", anchor="w", justify="left")
        self.library_count.pack(anchor="w", padx=5, pady=(13, 0))
        self.credit_link = self._label(footer, "Made by Radsharkboy", 7, "MUTED", cursor="hand2",
                                      takefocus=True, highlightthickness=1)
        self.theme.bind(self.credit_link, highlightbackground="BG", highlightcolor="ACCENT")
        self.credit_link.pack(anchor="w", padx=4, pady=(2, 0))
        for event in ("<ButtonRelease-1>", "<Return>", "<space>"):
            self.credit_link.bind(event, self._open_project)
        for event in ("<Enter>", "<FocusIn>"):
            self.credit_link.bind(event, lambda event: self._credit_highlight(True))
        for event in ("<Leave>", "<FocusOut>"):
            self.credit_link.bind(event, lambda event: self._credit_highlight(False))
        self._build_nav()

    def _credit_highlight(self, active):
        active = active or self.root.focus_get() is self.credit_link
        self.theme.bind(self.credit_link, fg="ACCENT" if active else "MUTED")

    def _open_project(self, event=None):
        url = "https://github.com/Rad-Sharkboy/Algorithm-Visualizer"
        try:
            opened = webbrowser.open_new_tab(url)
        except (webbrowser.Error, OSError):
            opened = False
        if not opened:
            self.message.configure(text=f"Project: {url}")
            self.theme.bind(self.message, fg="MUTED")
        return "break"

    def _build_nav(self):
        names = [name for name, meta in ALGORITHMS.items() if meta.category == self.category]
        self.algorithm_list.set_names(names)
        self.nav_buttons = {name: NavigationAction(self.algorithm_list, name) for name in names}

    def _refresh_nav(self):
        for category, button in self.tab_buttons.items():
            button.configure(selected=category == self.category)
        self.algorithm_list.select(self.algorithm)

    def _build_main(self):
        main = self.theme.frame(self.root)
        main.pack(side="left", fill="both", expand=True, padx=SPACING["outer"], pady=22)
        self.main = main
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)
        header = self.theme.frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        eyebrow = self.theme.frame(header)
        eyebrow.pack(fill="x")
        self._label(eyebrow, "S O R T I N G  /  S E A R C H I N G", 7, "MUTED").pack(side="left")
        self.theme_box = InstrumentSelect(eyebrow, self.theme, self.manager, self.reduced_motion,
                                          self.theme_var, tuple(THEME_LABELS), width=144, labels=THEME_LABELS)
        self.theme_box.pack(side="right")
        self.theme_box.bind("<<ComboboxSelected>>", self._change_theme)
        self.title = DisplayTitle(header, self.theme, self.manager, self.reduced_motion)
        self.title.pack(fill="x")
        self._label(header, "Observe the structure. Follow the signal.", 9, "MUTED").pack(anchor="w")
        info = self.theme.frame(main)
        info.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.algo_title = self._label(info, size=11, bold=True)
        self.algo_title.pack(side="left")
        self.complexity_label = self._label(info, size=8, role="MUTED")
        self.complexity_label.pack(side="left", padx=16)
        self.state_label = StatusLamp(info, self.theme, self.manager, self.reduced_motion)
        self.state_label.pack(side="right")
        self.meters = MeterRow(main, self.theme, self.manager, self.reduced_motion)
        self.meters.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        self.stat_labels = {key: MeterValue(self.meters, key) for key in self.meters.values}
        scope_frame = self.theme.frame(main, role="PANEL", highlightthickness=1)
        self.theme.bind(scope_frame, highlightbackground="BORDER")
        scope_frame.grid(row=3, column=0, sticky="nsew")
        scope_frame.columnconfigure(0, weight=1)
        scope_frame.rowconfigure(0, weight=1)
        self.chart_card = scope_frame
        self.canvas = ScopeScreen(scope_frame, self.theme, self.manager, self.reduced_motion)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 0))
        legend = self.theme.frame(scope_frame, role="INSET")
        legend.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        for name, role in (("SIGNAL", "BAR"), ("COMPARE", "COMPARE"), ("PIVOT", "PIVOT"), ("SETTLED", "SETTLED")):
            self.theme.frame(legend, role=role, width=9, height=2).pack(side="left", padx=(14, 5), pady=10)
            self._label(legend, name, 7, "MUTED", bg="INSET").pack(side="left")
        self.array_count = self._label(legend, "", 7, "MUTED", bg="INSET")
        self.array_count.pack(side="right", padx=12)
        self.message = self._label(scope_frame, "", 9, "TEXT", bg="PANEL", anchor="w", justify="left", padx=14, pady=11, wraplength=700)
        self.message.grid(row=2, column=0, sticky="ew")
        self.message.bind("<Configure>", lambda event: self.message.configure(wraplength=max(100, event.width - 28)))
        controls = self.theme.frame(main)
        controls.grid(row=4, column=0, sticky="ew", pady=(16, 16))
        self.run_button = self._button(controls, "Run", self.toggle_run, "play", width=144, primary=True, height=44)
        self.run_button.pack(side="left")
        self.step_button = self._button(controls, "Step", self.step_once, "step", width=96)
        self.step_button.pack(side="left", padx=(7, 0))
        self.stop_button = self._button(controls, "Stop", self.stop, "stop", width=82)
        self.stop_button.pack(side="left", padx=(7, 0))
        self.reset_button = self._button(controls, "Reset", self.reset, "reset", width=102)
        self.reset_button.pack(side="left", padx=(7, 0))
        speed = self.theme.frame(controls)
        speed.pack(side="right")
        self.speed_label = self._label(speed, "", 7, "MUTED")
        self.speed_label.pack(anchor="e")
        self.speed_scale = InstrumentSlider(speed, self.theme, self.manager, self.speed_var, self._speed_changed, self.reduced_motion, length=175)
        self.speed_scale.pack()
        self._speed_changed()
        data = self.theme.frame(main)
        data.grid(row=5, column=0, sticky="ew")
        self.theme.frame(data, role="BORDER", height=1).pack(fill="x", pady=(0, 10))
        data_top = self.theme.frame(data)
        data_top.pack(fill="x", pady=(0, 10))
        self._label(data_top, "I N P U T", 7, "MUTED").pack(side="left", padx=(0, 12))
        self.preset_box = InstrumentSelect(data_top, self.theme, self.manager, self.reduced_motion,
                                           self.preset_var, ("Random", "Nearly sorted", "Reversed", "Few unique"), width=166)
        self.preset_box.pack(side="left")
        self.size_label = self._label(data_top, "28 values", 8, "MUTED")
        self.size_label.pack(side="left", padx=(12, 8))
        self.size_scale = InstrumentSlider(data_top, self.theme, self.manager, self.size_var, self._size_changed,
                                            self.reduced_motion, from_=8, to=64, length=94)
        self.size_scale.pack(side="left", fill="x", expand=True)
        self.shuffle_button = self._button(data_top, "Generate", self.new_array, "generate", width=124, height=36)
        self.shuffle_button.pack(side="right", padx=(10, 0))
        data_bottom = self.theme.frame(data)
        data_bottom.pack(fill="x")
        self._label(data_bottom, "VALUES", 8, "MUTED").pack(side="left", padx=(0, 12))
        self.custom_entry = self._entry(data_bottom, self.custom_var)
        self.custom_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.custom_entry.bind("<Return>", lambda event: self.apply_custom())
        self.apply_button = self._button(data_bottom, "Apply", self.apply_custom, width=76, height=36)
        self.apply_button.pack(side="left", padx=(7, 0))
        self.target_box = self.theme.frame(data_bottom)
        self._label(self.target_box, "TARGET", 8, "MUTED").pack(side="left", padx=(10, 7))
        self.target_entry = self._entry(self.target_box, self.target_var, width=5)
        self.target_entry.pack(side="left", ipady=7)
        self.target_entry.bind("<Return>", lambda event: self.toggle_run())
        learn = self.theme.frame(main)
        self.learn = learn
        learn.grid(row=6, column=0, sticky="ew", pady=(18, 0))
        learn.columnconfigure(0, weight=1, uniform="learn")
        learn.columnconfigure(1, weight=1, uniform="learn")
        about = self.theme.frame(learn)
        about.grid(row=0, column=0, sticky="nw", padx=(0, 20))
        self._label(about, "M E T H O D  /  N O T E S", 7, "MUTED").pack(anchor="w", pady=(3, 4))
        self.summary_label = self._label(about, "", 8, "MUTED", justify="left", wraplength=330)
        self.summary_label.pack(anchor="w", pady=(6, 0))
        self.space_label = self._label(about, "", 7, "MUTED", justify="left")
        self.space_label.pack(anchor="w", pady=(6, 0))
        code = self.theme.frame(learn, role="INSET")
        code.grid(row=0, column=1, sticky="nsew")
        self.code_labels = []
        for index in range(6):
            row = self._label(code, "", 8, "MUTED", bg="INSET", anchor="w", padx=9, pady=2)
            row.pack(fill="x")
            self.code_labels.append(row)
        self.guide_button = self._button(header, "Guide", self.show_guide, "guide", width=96, height=26)
        self.guide_button.place(relx=1, rely=1, anchor="se")
        self._bar_bounds = []

    def _entry(self, parent, variable, width=None):
        return InstrumentEntry(parent, self.theme, self.manager, self.reduced_motion,
                               textvariable=variable, width=width)

    def _resize(self, event):
        if event.widget is self.root and hasattr(self, "learn"):
            if event.height < 870:
                self.learn.grid_remove()
            else:
                self.learn.grid()

    def show_guide(self):
        meta = ALGORITHMS[self.algorithm]
        guide = tk.Toplevel(self.root)
        guide.title(f"{meta.name} · Algorithm guide")
        guide.geometry("610x440")
        guide.transient(self.root)
        self.theme.bind(guide, bg="PANEL")
        self._label(guide, meta.name.upper(), 17, bg="PANEL").pack(anchor="w", padx=24, pady=(24, 12))
        self._label(guide, meta.summary, 10, "MUTED", bg="PANEL", wraplength=555, justify="left").pack(anchor="w", padx=24)
        self._label(guide, f"Average {meta.average} / Worst {meta.worst} / Space {meta.space}",
                    9, "ACCENT", bg="PANEL").pack(anchor="w", padx=24, pady=16)
        for index, line in enumerate(meta.code, 1):
            self._label(guide, f"{index:02}  {line}", 9, bg="PANEL", anchor="w").pack(fill="x", padx=24, pady=3)
        self._label(guide, "Algorithm costs exclude visualization. Writes count main-array assignments.",
                    8, "MUTED", bg="PANEL", wraplength=540).pack(anchor="w", padx=24, pady=16)
        guide.bind("<Escape>", lambda event: guide.destroy())

    def _set_category(self, category):
        if category == self.category:
            return
        self.category = category
        self._build_nav()
        self._select_algorithm("Merge Sort" if category == "Sort" else "Linear Search")

    def _select_algorithm(self, name):
        self._cancel()
        self.algorithm = name
        meta = ALGORITHMS[name]
        if meta.category != self.category:
            self.category = meta.category
            self._build_nav()
        self.title.set_text("Sorting, made visible." if self.category == "Sort" else "Searching, made visible.")
        self.algo_title.configure(text=name.upper())
        self.complexity_label.configure(text=f"AVG {meta.average}")
        self.summary_label.configure(text=meta.summary)
        self.space_label.configure(text=f"WORST {meta.worst} / SPACE {meta.space}")
        for index, text in enumerate(meta.code):
            self.code_labels[index].configure(text=f"{index + 1:02}  {text}")
        if meta.category == "Search":
            self.target_box.pack(side="left")
        else:
            self.target_box.pack_forget()
        self.reset()
        self._refresh_nav()

    def _size_changed(self, value):
        self.size_label.configure(text=f"{round(float(value))} values")

    def _speed_changed(self, value=None):
        self.speed_label.configure(text=f"ANIMATION SPEED   {120 / self.interval:.1f}×")

    @property
    def interval(self):
        return max(6, round(650 * (0.01 ** (self.speed_var.get() / 100))))

    def new_array(self):
        self.set_data(generate_values(self.size_var.get(), self.preset_var.get()))

    def apply_custom(self):
        try:
            values = parse_values(self.custom_var.get())
        except ValueError as error:
            self.pause()
            self.message.configure(text=f"Check your input · {error}", fg=self.palette.COMPARE)
            self.theme.bind(self.message, fg="COMPARE")
            return
        self.set_data(values)

    def set_data(self, values):
        self._cancel()
        self.original = list(values)
        self.custom_var.set(", ".join(map(str, values)))
        if len(values) >= 8:
            self.size_var.set(len(values))
            self._size_changed(len(values))
        self.reset()

    def _reset_metrics(self):
        self.comparisons = self.writes = self.steps = 0
        self.elapsed = 0.0
        self._active_since = None
        self._update_stats()

    def reset(self):
        self._cancel()
        self._iterator = None
        self._reset_metrics()
        self.arr = self.original.copy()
        self.current = Step(tuple(self.arr), "Ready when you are. Run the animation or explore one step at a time.")
        self.state = "ready"
        self._render()

    def _prepare(self):
        target = None
        if ALGORITHMS[self.algorithm].category == "Search":
            try:
                target = int(self.target_var.get())
                if not -999 <= target <= 999:
                    raise ValueError
            except ValueError:
                self.message.configure(text="Choose a target · Enter an integer between −999 and 999.", fg=self.palette.COMPARE)
                self.theme.bind(self.message, fg="COMPARE")
                return False
        self._reset_metrics()
        values = self.original.copy()
        if self.algorithm in ("Binary Search", "Interpolation Search"):
            values.sort()
            preparation = Step(tuple(values), f"Input sorted for {self.algorithm.lower()}. "
                               "Indices refer to this order; preparation is not counted.")
            self._iterator = itertools.chain((preparation,), ALGORITHMS[self.algorithm].function(values, target))
        else:
            self._iterator = ALGORITHMS[self.algorithm].function(values, target)
        self.arr = values
        return True

    def toggle_run(self):
        if self.state == "running":
            self.pause()
            return
        if self.state != "paused" and not self._prepare():
            return
        self.state = "running"
        self._active_since = time.perf_counter()
        self._sync_controls()
        self._tick()

    def pause(self):
        if self.state != "running":
            return
        self._cancel()
        self.state = "paused"
        self._sync_controls()
        self._update_stats()
        self._draw()

    def step_once(self):
        if self.state == "running":
            self.pause()
        if self.state != "paused" and not self._prepare():
            return
        self.state = "paused"
        self._advance()

    def stop(self):
        if self.state not in ("running", "paused"):
            return
        self._cancel()
        self._iterator = None
        # Shifts and merges temporarily duplicate values. Cancellation restores
        # the input instead of leaving an incomplete write as the next dataset.
        self.arr = self.original.copy()
        self.current = Step(tuple(self.arr), "Stopped. Your original input is restored and ready to run again.")
        self.state = "stopped"
        self._render()

    def _cancel(self):
        self._stop_motion()
        if self._after_id is not None:
            self.manager.cancel(self._after_id)
            self._after_id = None
        if self._active_since is not None:
            self.elapsed += time.perf_counter() - self._active_since
            self._active_since = None

    def _tick(self):
        self._after_id = None
        if self._closed or self.state != "running":
            return
        self._advance()
        if self.state == "running":
            self._after_id = self.manager.call_later(self.interval, self._tick)

    def _advance(self):
        if self._iterator is None:
            return
        previous = self.current
        was_running = self.state == "running"
        try:
            self.current = next(self._iterator)
        except StopIteration:
            self._cancel()
            self._iterator = None
            self.state = "done"
            self._render()
            return
        self.arr = list(self.current.values)
        self.steps += 1
        self.comparisons += self.current.comparisons
        self.writes += self.current.writes
        if self.current.done:
            self._cancel()
            self._iterator = None
            self.state = "done"
        self._render(animate_from=previous if was_running else None)

    def _update_stats(self):
        elapsed = self.elapsed + (time.perf_counter() - self._active_since if self._active_since is not None else 0)
        self.meters.set(comparisons=self.comparisons, writes=self.writes, steps=self.steps, elapsed=elapsed)

    def _sync_controls(self):
        busy = self.state in ("running", "paused")
        self.run_button.set_playback(self.state)
        self.stop_button.configure(state="normal" if busy else "disabled")
        self.target_entry.configure(state="disabled" if busy else "normal")
        not_found = self.state == "done" and self.category == "Search" and self.current.result is None
        status = "not_found" if not_found else "finishing" if self._completing else self.state
        self.state_label.set(status)
        self.canvas.set_running(self.state == "running")

    def _render(self, animate_from=None):
        finish = self.current.done and (self.category == "Sort" or bool(self.current.found))
        self._completing = finish
        self._update_stats()
        self._sync_controls()
        not_found = self.current.done and self.category == "Search" and self.current.result is None
        self.message.configure(text=self.current.message)
        self.theme.bind(self.message, fg="COMPARE" if not_found else "SETTLED" if self.current.done else "TEXT")
        self.array_count.configure(text=f"{len(self.arr):02} VALUES")
        for index, row in enumerate(self.code_labels):
            self.theme.bind(row, fg="ACCENT" if self.steps and index == self.current.line else "MUTED")
        reset = self.steps == 0 or self.state == "stopped"
        self.canvas.set_step(self.current, self.steps, duration=max(.07, min(.35, self.interval * .0015)),
                             animate=animate_from is not None, reset=reset)
        self._bar_bounds = self.canvas._bounds
        self._motion_id = self.canvas.key + ":move" if animate_from is not None and not self.reduced_motion.get() else None
        if finish:
            self._finish_progress = 0
            self.canvas.complete(self._completion_done)

    def _completion_done(self):
        self._completing = False
        self._finish_progress = 1
        self._motion_id = None
        self._sync_controls()

    def _draw(self, event=None):
        self.canvas.paint()
        self._bar_bounds = self.canvas._bounds

    def _hover(self, event):
        self.canvas._hover(event)

    def _stop_motion(self):
        if hasattr(self, "canvas"):
            self.canvas.set_running(False)
            self.canvas.settle(keep_positions=self.state == "running" and not self.reduced_motion.get())
            self.meters.settle()
            self.title.settle()
            self.algorithm_list.settle()
            self.state_label.manager.cancel(self.state_label.key + ":pulse")
        if self._launch_id is not None:
            self.manager.cancel(self._launch_id)
            self._launch_id = None
        self._completing = False
        self._motion_id = None
        self._motion_progress = self._finish_progress = 1.0

    def _launch(self):
        self._launch_id = None
        if self._closed or self.reduced_motion.get() or self.state != "ready":
            return
        self.title.launch()
        self.algorithm_list.launch()
        self.canvas.launch()

    def _motion_preference_changed(self):
        self._stop_motion()
        if self.reduced_motion.get():
            self.manager.finish_tweens()
        for widget in (self.run_button, self.motion_toggle, self.speed_scale, self.size_scale):
            widget.motion_changed()
        self._sync_controls()

    def _typing(self):
        return isinstance(self.root.focus_get(), (tk.Entry, InstrumentSelect, InstrumentSlider))

    def _space(self, event):
        if not self._typing() and not isinstance(self.root.focus_get(), (AnimatedButton, Navigation)):
            self.toggle_run()
            return "break"

    def _right(self, event):
        if not self._typing():
            self.step_once()
            return "break"

    def close(self):
        self._cancel()
        self._closed = True
        self.manager.close()
        self._theme_id = None
        self.root.destroy()


class NavigationAction:
    def __init__(self, navigation, name):
        self.navigation, self.name = navigation, name

    def invoke(self):
        self.navigation.command(self.name)

    def __getattr__(self, key):
        return getattr(self.navigation, key)


class MeterValue:
    def __init__(self, row, key):
        self.row, self.key = row, key

    def cget(self, option):
        value = self.row.targets[self.key]
        return f"{value:.1f}s" if self.key == "elapsed" else str(round(value))


def main():
    root = tk.Tk()
    Visualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
