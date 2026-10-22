"""Algo Studio — an interactive, standard-library-only algorithm visualizer."""

import itertools
import math
import time
import tkinter as tk
from tkinter import ttk

from algorithms import ALGORITHMS, Step
from datasets import generate_values, parse_values
from motion import bar_poses, blend, ease
from theme import StudioTheme
from widgets import GlassButton, MotionToggle


class Visualizer:
    def __init__(self, root):
        self.root = root
        self.theme = StudioTheme(root)
        self.font, self.mono = self.theme.font, self.theme.mono
        self._label = self.theme.label
        self._button = self.theme.button
        self.theme_var = tk.StringVar(value="System")
        self._theme_id = None
        root.title("Algo Studio · Algorithm Visualizer")
        root.configure(bg=self.palette.BG)
        window_width = min(1280, max(1000, root.winfo_screenwidth() - 60))
        window_height = min(860, max(740, root.winfo_screenheight() - 60))
        root.geometry(f"{window_width}x{window_height}")
        root.minsize(1000, 740)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._closed = False
        self._after_id = None
        self._motion_id = None
        self._motion_progress = 1.0
        self._finish_progress = 1.0
        self._previous_step = None
        self._iterator = None
        self.state = "ready"
        self.comparisons = self.writes = self.steps = 0
        self.elapsed = 0.0
        self._active_since = None
        self.category = "Sort"
        self.algorithm = "Merge Sort"
        self.original = []
        self.arr = []
        self.current = Step((), "Choose an algorithm, then press Run.")
        self.size_var = tk.DoubleVar(value=28)
        self.speed_var = tk.DoubleVar(value=32)
        self.reduced_motion = tk.BooleanVar(value=False)
        self.target_var = tk.StringVar(value="50")
        self.preset_var = tk.StringVar(value="Random")
        self.custom_var = tk.StringVar()
        self._configure_styles()
        self._build_sidebar()
        self._build_main()
        self._select_algorithm(self.algorithm)
        self.new_array()
        root.bind("<space>", self._space)
        root.bind("<Escape>", lambda event: self.stop())
        root.bind("<Control-r>", lambda event: self.reset())
        root.bind("<Right>", self._right)
        root.bind("<Configure>", self._resize)
        self._theme_id = root.after(2000, self._poll_theme)

    @property
    def palette(self):
        return self.theme.palette

    def _change_theme(self, event=None):
        if self.theme.select(self.theme_var.get()):
            self._configure_styles()
            self._refresh_nav()
            # Redraw the current frame without advancing or cancelling its tween.
            self._draw()

    def _poll_theme(self):
        self._theme_id = None
        if self._closed:
            return
        if self.theme_var.get() == "System":
            self._change_theme()
        self._theme_id = self.root.after(2000, self._poll_theme)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Studio.TCombobox", fieldbackground=self.palette.INSET, background=self.palette.BORDER,
                        foreground=self.palette.TEXT, arrowcolor=self.palette.ACCENT, bordercolor=self.palette.BORDER,
                        lightcolor=self.palette.BORDER, darkcolor=self.palette.BORDER, padding=7,
                        font=(self.font, 9))
        style.map("Studio.TCombobox", fieldbackground=[("readonly", self.palette.INSET)],
                  foreground=[("readonly", self.palette.TEXT)],
                  selectbackground=[("readonly", self.palette.INSET)],
                  selectforeground=[("readonly", self.palette.TEXT)])
        style.configure("Studio.Horizontal.TScale", background=self.palette.ACCENT,
                        troughcolor=self.palette.INSET, bordercolor=self.palette.BORDER,
                        lightcolor=self.palette.ACCENT, darkcolor=self.palette.ACCENT,
                        sliderlength=18, sliderrelief="flat", borderwidth=0)
        self.root.option_add("*TCombobox*Listbox.background", self.palette.INSET)
        self.root.option_add("*TCombobox*Listbox.foreground", self.palette.TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.palette.SELECT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", self.palette.ACCENT)
        # Option defaults only affect new popups. Recolor any already-created
        # dropdown too, including the theme menu that initiated this change.
        for name in ("theme_box", "preset_box"):
            box = getattr(self, name, None)
            if box is not None:
                popdown = self.root.tk.call("ttk::combobox::PopdownWindow", str(box))
                listing = f"{popdown}.f.l"
                if self.root.tk.call("winfo", "exists", listing):
                    self.root.tk.call(listing, "configure", "-background", self.palette.INSET,
                                      "-foreground", self.palette.TEXT,
                                      "-selectbackground", self.palette.SELECT,
                                      "-selectforeground", self.palette.ACCENT)

    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=self.palette.SIDEBAR, width=232)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=self.palette.SIDEBAR)
        brand.pack(fill="x", padx=22, pady=(22, 16))
        mark = tk.Canvas(brand, width=36, height=36, bg=self.palette.SIDEBAR, highlightthickness=0)
        mark.pack(side="left", padx=(0, 10))
        for x, h in ((3, 14), (13, 29), (23, 21)):
            mark.create_rectangle(x, 33 - h, x + 6, 33, fill=self.palette.ACCENT, outline="")
        names = tk.Frame(brand, bg=self.palette.SIDEBAR)
        names.pack(side="left")
        self._label(names, "ALGO STUDIO", 12, bold=True, anchor="w").pack(anchor="w")
        self._label(names, "IDEAS IN MOTION", 7, self.palette.MUTED).pack(anchor="w")
        tk.Frame(self.sidebar, bg=self.palette.BORDER, height=1).pack(fill="x", padx=20)
        self._label(self.sidebar, "THE ALGORITHM LIBRARY", 8, self.palette.MUTED, bold=True).pack(
            anchor="w", padx=22, pady=(18, 10))
        tabs = tk.Frame(self.sidebar, bg=self.palette.INSET)
        tabs.pack(fill="x", padx=18)
        self.tab_buttons = {}
        for category in ("Sort", "Search"):
            tab = tk.Button(tabs, text=category.upper(), bd=0, relief="flat",
                            font=(self.font, 9, "bold"), pady=9, cursor="hand2",
                            command=lambda c=category: self._set_category(c),
                            highlightthickness=1, highlightcolor=self.palette.ACCENT)
            tab.pack(side="left", fill="x", expand=True)
            self.tab_buttons[category] = tab
        self.algorithm_list = tk.Frame(self.sidebar, bg=self.palette.SIDEBAR)
        self.algorithm_list.pack(fill="x", padx=18, pady=12)
        self.nav_buttons = {}
        self._build_nav()
        footer = tk.Frame(self.sidebar, bg=self.palette.SIDEBAR)
        footer.pack(side="bottom", fill="x", padx=22, pady=14)
        self._label(footer, "LEARN BY DOING", 8, self.palette.ACCENT, bold=True).pack(anchor="w")
        self._label(footer, "Space   Run / Pause\n→         Next step\nEsc       Stop\nCtrl+R  Reset input",
              9, self.palette.MUTED, justify="left", anchor="w").pack(anchor="w", pady=(8, 10))
        tk.Frame(footer, bg=self.palette.BORDER, height=1).pack(fill="x", pady=(0, 12))
        self.motion_toggle = MotionToggle(
            footer, self.theme, self.reduced_motion, self._motion_preference_changed)
        self.motion_toggle.pack(anchor="w", pady=(0, 8))
        self.library_count = self._label(footer, f"{len(ALGORITHMS)} algorithms. Endless discoveries.", 7, self.palette.MUTED)
        self.library_count.pack(anchor="w")

    def _build_nav(self):
        for widget in self.algorithm_list.winfo_children():
            widget.destroy()
        self.nav_buttons.clear()
        for index, (name, algorithm) in enumerate(
                (item for item in ALGORITHMS.items() if item[1].category == self.category), 1):
            nav = tk.Button(self.algorithm_list, text=f"{index:02}   {name}",
                            command=lambda n=name: self._select_algorithm(n),
                            anchor="w", padx=12, pady=3, bd=0, relief="flat",
                            cursor="hand2", font=(self.font, 10), highlightthickness=1,
                            highlightcolor=self.palette.ACCENT)
            nav.pack(fill="x", pady=1)
            self.nav_buttons[name] = nav
        self._refresh_nav()

    def _refresh_nav(self):
        for category, tab in self.tab_buttons.items():
            selected = category == self.category
            tab.configure(bg=self.palette.BORDER if selected else self.palette.INSET,
                          fg=self.palette.TEXT if selected else self.palette.MUTED, activebackground=self.palette.BORDER,
                          activeforeground=self.palette.TEXT, highlightbackground=self.palette.INSET)
        for name, nav in self.nav_buttons.items():
            selected = name == self.algorithm
            nav.configure(bg=self.palette.SELECT if selected else self.palette.SIDEBAR,
                          fg=self.palette.ACCENT if selected else self.palette.MUTED,
                          activebackground=self.palette.HOVER, activeforeground=self.palette.TEXT,
                          highlightbackground=self.palette.SELECT_BORDER if selected else self.palette.SIDEBAR)

    def _build_main(self):
        main = tk.Frame(self.root, bg=self.palette.BG)
        main.pack(side="left", fill="both", expand=True, padx=28, pady=24)
        self.main = main
        header = tk.Frame(main, bg=self.palette.BG)
        header.pack(fill="x", pady=(0, 18))
        eyebrow = tk.Frame(header, bg=self.palette.BG)
        eyebrow.pack(fill="x")
        self._label(eyebrow, "EXPLORE / UNDERSTAND / EXPERIMENT", 8, self.palette.ACCENT, bold=True).pack(side="left")
        self.guide_button = tk.Button(
            eyebrow, text="Algorithm guide  ↗", command=self.show_guide, bg=self.palette.BG, fg=self.palette.MUTED,
            activebackground=self.palette.BG, activeforeground=self.palette.ACCENT, bd=0, cursor="hand2",
            font=(self.font, 8), highlightthickness=0)
        self.guide_button.pack(side="right")
        title_row = tk.Frame(header, bg=self.palette.BG)
        title_row.pack(fill="x", pady=(6, 3))
        self.title = self._label(title_row, "Sorting, made visible.", 25, bold=True)
        self.title.pack(side="left")
        appearance = tk.Frame(title_row, bg=self.palette.BG)
        appearance.pack(side="right")
        self._label(appearance, "THEME", 7, self.palette.MUTED, bold=True).pack(side="left", padx=(0, 8))
        self.theme_box = ttk.Combobox(appearance, textvariable=self.theme_var,
                                     values=("System", "Light", "Dark"), width=7,
                                     state="readonly", style="Studio.TCombobox")
        self.theme_box.pack(side="left")
        self.theme_box.bind("<<ComboboxSelected>>", self._change_theme)
        self._label(header, "Small steps. Big ideas. Watch an algorithm come to life.", 10, self.palette.MUTED).pack(anchor="w")
        info = tk.Frame(main, bg=self.palette.BG)
        info.pack(fill="x", pady=(0, 14))
        self.algo_title = self._label(info, size=15, bold=True)
        self.algo_title.pack(side="left")
        self.complexity_label = self._label(info, size=9, color=self.palette.MUTED)
        self.complexity_label.pack(side="left", padx=16)
        self.state_label = self._label(info, "●  READY", 9, self.palette.ACCENT, bold=True, bg=self.palette.SELECT, padx=12, pady=6)
        self.state_label.pack(side="right")
        stats = tk.Frame(main, bg=self.palette.BG)
        stats.pack(fill="x", pady=(0, 14))
        self.stat_labels = {}
        for index, (key, title, color) in enumerate((
                ("comparisons", "COMPARISONS", self.palette.PURPLE), ("writes", "ARRAY WRITES", self.palette.ACCENT),
                ("steps", "VISUAL STEPS", self.palette.GOLD), ("elapsed", "ACTIVE TIME", self.palette.TEXT))):
            stats.columnconfigure(index, weight=1, uniform="stat")
            card = tk.Frame(stats, bg=self.palette.PANEL, highlightbackground=self.palette.BORDER, highlightthickness=1)
            card.grid(row=0, column=index, sticky="ew",
                      padx=(0 if index == 0 else 5, 0 if index == 3 else 5))
            self._label(card, title, 8, self.palette.MUTED, bold=True).pack(anchor="w", padx=14, pady=(11, 3))
            number = self._label(card, "0.0s" if key == "elapsed" else "0", 22, color, bold=True)
            number.pack(anchor="w", padx=14, pady=(0, 10))
            self.stat_labels[key] = number
        self.chart_card = tk.Frame(main, bg=self.palette.PANEL, highlightbackground=self.palette.BORDER, highlightthickness=1)
        self.chart_card.pack(fill="both", expand=True)
        chart_top = tk.Frame(self.chart_card, bg=self.palette.PANEL)
        chart_top.pack(fill="x", padx=18, pady=(13, 0))
        self._label(chart_top, "THE ARRAY", 8, self.palette.MUTED, bold=True).pack(side="left")
        self.array_count = self._label(chart_top, "", 8, self.palette.MUTED)
        self.array_count.pack(side="right")
        self.canvas = tk.Canvas(self.chart_card, bg=self.palette.PANEL, highlightthickness=0, height=210)
        self.canvas.pack(fill="both", expand=True, padx=10)
        self.canvas.bind("<Configure>", self._draw)
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda event: self.canvas.delete("tooltip"))
        self._bar_bounds = []
        legend = tk.Frame(self.chart_card, bg=self.palette.PANEL)
        legend.pack(fill="x", padx=18, pady=(2, 12))
        for text, color in (("Unvisited", self.palette.ACCENT), ("Comparing", self.palette.PURPLE), ("Pivot / bound", self.palette.GOLD),
                            ("Settled / found", self.palette.GREEN)):
            self._label(legend, "●", 10, color).pack(side="left", padx=(0, 5))
            self._label(legend, text, 8, self.palette.MUTED).pack(side="left", padx=(0, 17))
        self.message = self._label(self.chart_card, "", 10, self.palette.TEXT, bg=self.palette.INSET, anchor="w",
                             justify="left", padx=16, pady=12, wraplength=650)
        self.message.pack(fill="x")
        self.message.bind("<Configure>", lambda event: self.message.configure(
            wraplength=max(100, event.width - 32)))
        chart_sections = (chart_top, self.canvas, legend, self.message)
        for widget in chart_sections:
            widget.pack_forget()
        for row, widget in enumerate(chart_sections):
            widget.grid(row=row, column=0, sticky="nsew" if row == 1 else "ew",
                        padx=10 if row == 1 else (0 if row == 3 else 18),
                        pady=(13, 0) if row == 0 else ((2, 10) if row == 2 else 0))
        self.chart_card.columnconfigure(0, weight=1)
        self.chart_card.rowconfigure(1, weight=1)
        controls = tk.Frame(main, bg=self.palette.BG)
        controls.pack(fill="x", pady=(14, 12))
        self.run_button = GlassButton(controls, self.theme, self.toggle_run, self.reduced_motion)
        self.run_button.pack(side="left")
        self.step_button = self._button(controls, "Step →", self.step_once)
        self.step_button.pack(side="left", padx=(7, 0))
        self.stop_button = self._button(controls, "Stop", self.stop)
        self.stop_button.pack(side="left", padx=(7, 0))
        self.reset_button = self._button(controls, "↺  Reset", self.reset)
        self.reset_button.pack(side="left", padx=(7, 0))
        speed_box = tk.Frame(controls, bg=self.palette.BG)
        speed_box.pack(side="right")
        self.speed_label = self._label(speed_box, "", 8, self.palette.MUTED)
        self.speed_label.pack(anchor="e")
        self.speed_scale = ttk.Scale(speed_box, from_=0, to=100, variable=self.speed_var,
                                     command=self._speed_changed, length=145,
                                     style="Studio.Horizontal.TScale")
        self.speed_scale.pack()
        self._speed_changed()
        data = tk.Frame(main, bg=self.palette.PANEL, highlightbackground=self.palette.BORDER, highlightthickness=1)
        data.pack(fill="x", pady=(0, 12))
        data_top = tk.Frame(data, bg=self.palette.PANEL)
        data_top.pack(fill="x", padx=14, pady=(10, 8))
        self._label(data_top, "INPUT", 8, self.palette.MUTED, bold=True).pack(side="left", padx=(0, 12))
        self.preset_box = ttk.Combobox(data_top, textvariable=self.preset_var,
                                      values=("Random", "Nearly sorted", "Reversed", "Few unique"),
                                      width=13, state="readonly", style="Studio.TCombobox")
        self.preset_box.pack(side="left")
        self.size_label = self._label(data_top, "28 values", 8, self.palette.MUTED)
        self.size_label.pack(side="left", padx=(12, 6))
        self.size_scale = ttk.Scale(data_top, from_=8, to=64, variable=self.size_var,
                                    command=self._size_changed, length=90,
                                    style="Studio.Horizontal.TScale")
        self.size_scale.pack(side="left", fill="x", expand=True)
        self.shuffle_button = self._button(data_top, "↻  Generate", self.new_array)
        self.shuffle_button.pack(side="right", padx=(8, 0))
        data_bottom = tk.Frame(data, bg=self.palette.PANEL)
        data_bottom.pack(fill="x", padx=14, pady=(0, 10))
        self._label(data_bottom, "YOUR DATA", 8, self.palette.MUTED, bold=True).pack(side="left", padx=(0, 10))
        self.custom_entry = self._entry(data_bottom, self.custom_var)
        self.custom_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.custom_entry.bind("<Return>", lambda event: self.apply_custom())
        self.apply_button = self._button(data_bottom, "Apply", self.apply_custom)
        self.apply_button.pack(side="left", padx=(7, 0))
        self.target_box = tk.Frame(data_bottom, bg=self.palette.PANEL)
        self._label(self.target_box, "TARGET", 8, self.palette.GOLD, bold=True).pack(side="left", padx=(12, 7))
        self.target_entry = self._entry(self.target_box, self.target_var, width=6)
        self.target_entry.pack(side="left", ipady=6)
        self.target_entry.bind("<Return>", lambda event: self.toggle_run())
        learn = tk.Frame(main, bg=self.palette.BG)
        self.learn = learn
        learn.pack(fill="x")
        learn.columnconfigure(0, weight=1, uniform="learn")
        learn.columnconfigure(1, weight=1, uniform="learn")
        about = tk.Frame(learn, bg=self.palette.BG)
        about.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        self._label(about, "BEHIND THE MOTION", 8, self.palette.ACCENT, bold=True).pack(anchor="w", pady=(0, 6))
        self.summary_label = self._label(about, "", 9, self.palette.MUTED, justify="left", anchor="nw", wraplength=350)
        self.summary_label.pack(fill="x")
        self.summary_label.bind("<Configure>", lambda event: self.summary_label.configure(
            wraplength=max(100, event.width)))
        self.space_label = self._label(about, "", 8, self.palette.MUTED, justify="left")
        self.space_label.pack(anchor="w", pady=(7, 0))
        code = tk.Frame(learn, bg=self.palette.INSET, padx=12, pady=7)
        code.grid(row=0, column=1, sticky="nsew")
        self.code_labels = []
        for index in range(6):
            row = tk.Label(code, text="", bg=self.palette.INSET, fg=self.palette.MUTED, anchor="w",
                           font=(self.mono, 8), pady=1)
            row.pack(fill="x")
            self.code_labels.append(row)
        # Reserve space for controls before giving the remaining area to bars.
        # Pack's sequential allocation would otherwise clip the bottom controls.
        sections = (header, info, stats, self.chart_card, controls, data, learn)
        for widget in sections:
            widget.pack_forget()
        for row, widget in enumerate(sections):
            widget.grid(row=row, column=0, sticky="nsew" if row == 3 else "ew",
                        pady=(0, 12) if row not in (3, 4, 6) else
                        ((12, 12) if row == 4 else 0))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1, minsize=130)

    def _resize(self, event):
        if event.widget is self.root:
            if event.height < 830:
                self.learn.grid_remove()
            else:
                self.learn.grid()

    def show_guide(self):
        meta = ALGORITHMS[self.algorithm]
        guide = tk.Toplevel(self.root)
        guide.title(f"{meta.name} · Algorithm guide")
        guide.configure(bg=self.palette.PANEL)
        guide.geometry("560x430")
        guide.transient(self.root)
        self._label(guide, meta.name, 22, bold=True).pack(anchor="w", padx=24, pady=(24, 12))
        self._label(guide, meta.summary, 11, self.palette.MUTED, wraplength=500,
              justify="left").pack(anchor="w", padx=24)
        self._label(guide, f"Average {meta.average}    Worst {meta.worst}    Space {meta.space}",
              10, self.palette.ACCENT).pack(anchor="w", padx=24, pady=16)
        for index, line in enumerate(meta.code, 1):
            tk.Label(guide, text=f"{index:02}  {line}", bg=self.palette.PANEL, fg=self.palette.TEXT,
                     font=(self.mono, 10), anchor="w").pack(fill="x", padx=24, pady=2)
        self._label(guide, "Complexities describe the algorithm, excluding visualization.\n"
              "Array writes count main-array assignments; time includes animation.",
              8, self.palette.MUTED, justify="left").pack(anchor="w", padx=24, pady=16)
        guide.bind("<Escape>", lambda event: guide.destroy())

    def _entry(self, parent, variable, width=None):
        return tk.Entry(parent, textvariable=variable, width=width, bg=self.palette.INSET, fg=self.palette.TEXT,
                        disabledbackground=self.palette.INSET, disabledforeground=self.palette.MUTED,
                        insertbackground=self.palette.ACCENT, relief="flat", font=(self.mono, 9),
                        highlightthickness=1, highlightbackground=self.palette.BORDER,
                        highlightcolor=self.palette.ACCENT, selectbackground=self.palette.SELECT_BORDER,
                        selectforeground=self.palette.TEXT)

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
        if self.category != meta.category:
            self.category = meta.category
            self._build_nav()
        self.title.configure(text="Sorting, made visible." if meta.category == "Sort" else "Find your next discovery.")
        self.algo_title.configure(text=name)
        self.complexity_label.configure(text=f"AVERAGE  {meta.average}")
        self.summary_label.configure(text=meta.summary)
        self.space_label.configure(text=f"Worst: {meta.worst}   ·   Space: {meta.space}\nAlgorithm costs exclude visualization snapshots.")
        for index, text in enumerate(meta.code):
            self.code_labels[index].configure(text=f"{index + 1:02}  {text}")
        if meta.category == "Search":
            self.target_box.pack(side="left")
        else:
            self.target_box.pack_forget()
        self._refresh_nav()
        self.reset()

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
            self.message.configure(text=f"Check your input · {error}", fg=self.palette.RED)
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
                self.message.configure(text="Choose a target · Enter an integer between −999 and 999.", fg=self.palette.RED)
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
            self.root.after_cancel(self._after_id)
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
            self._after_id = self.root.after(self.interval, self._tick)

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
        elapsed = self.elapsed
        if self._active_since is not None:
            elapsed += time.perf_counter() - self._active_since
        for key, value in (("comparisons", self.comparisons), ("writes", self.writes),
                           ("steps", self.steps), ("elapsed", f"{elapsed:.1f}s")):
            self.stat_labels[key].configure(text=str(value))

    def _sync_controls(self):
        busy = self.state in ("running", "paused")
        self.run_button.set_playback(self.state)
        self.stop_button.configure(state="normal" if busy else "disabled")
        # Dataset actions deliberately cancel a run; its parameters stay locked.
        self.target_entry.configure(state="disabled" if busy else "normal")
        state_text = {"ready": "●  READY", "running": "●  RUNNING", "paused": "Ⅱ  PAUSED",
                      "stopped": "■  STOPPED", "done": "✓  COMPLETE"}[self.state]
        not_found = self.state == "done" and self.category == "Search" and self.current.result is None
        self.state_label.configure(text="—  NOT FOUND" if not_found else state_text,
                                   fg=self.palette.GOLD if self.state == "paused" or not_found else self.palette.ACCENT)

    def _render(self, animate_from=None):
        self._update_stats()
        self._sync_controls()
        not_found = self.current.done and self.category == "Search" and self.current.result is None
        self.message.configure(text=self.current.message,
                               fg=self.palette.GOLD if not_found else self.palette.GREEN if self.current.done else self.palette.TEXT)
        self.array_count.configure(text=f"{len(self.arr)} VALUES   ·   ASCENDING" if self.category == "Sort"
                                   else f"{len(self.arr)} VALUES   ·   ZERO-BASED INDICES")
        for index, row in enumerate(self.code_labels):
            active = self.steps > 0 and index == self.current.line
            row.configure(fg=self.palette.ACCENT if active else self.palette.MUTED, bg=self.palette.SELECT if active else self.palette.INSET)
        self._stop_motion()
        if animate_from is not None and not self.reduced_motion.get():
            if self.current.done and (self.category == "Sort" or self.current.found):
                self._start_motion(finish=True)
                return
            if self.interval >= 32:
                self._previous_step = animate_from
                self._start_motion()
                return
        self._draw()

    def _stop_motion(self):
        if self._motion_id is not None:
            self.root.after_cancel(self._motion_id)
            self._motion_id = None
        self._motion_progress = self._finish_progress = 1.0

    def _motion_preference_changed(self):
        self.run_button.motion_changed()
        self.motion_toggle.motion_changed()
        self._stop_motion()
        self._draw()

    def _start_motion(self, finish=False):
        self._motion_started = time.perf_counter()
        self._motion_duration = .8 if finish else min(.32, self.interval * .00085)
        self._animate(finish)

    def _animate(self, finish=False):
        self._motion_id = None
        if self._closed:
            return
        progress = min(1.0, (time.perf_counter() - self._motion_started) / self._motion_duration)
        if finish:
            self._finish_progress = progress
        else:
            self._motion_progress = progress
        self._draw()
        if progress < 1:
            self._motion_id = self.root.after(16, lambda: self._animate(finish))

    def _colors(self, step):
        active, pivots = set(step.active), set(step.pivot)
        settled, found = set(step.settled), set(step.found)
        discarded = set(step.discarded)
        return [self.palette.GREEN if i in found or i in settled else
                self.palette.PURPLE if i in active else self.palette.GOLD if i in pivots else
                self.palette.DISCARDED if i in discarded else self.palette.ACCENT for i in range(len(step.values))]

    def _draw(self, event=None):
        if self._closed:
            return
        canvas = self.canvas
        canvas.delete("all")
        self._bar_bounds = []
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if not self.arr or width < 10 or height < 10:
            return
        left, right, top, bottom = 46, width - 16, 32, height - 40
        plot_height = max(20, bottom - top)
        # Keep the scale stable during transient merge/insertion writes.
        domain = self.original or self.arr
        low, high = min(0, min(domain)), max(0, max(domain))
        if low == high:
            high = low + 1

        def y(value):
            return bottom - (value - low) / (high - low) * plot_height

        for fraction in (0, .25, .5, .75, 1):
            value = low + (high - low) * fraction
            ypos = y(value)
            canvas.create_line(left, ypos, right, ypos, fill=self.palette.GRID, dash=(2, 5))
            canvas.create_text(left - 10, ypos, text=f"{value:.0f}", fill=self.palette.AXIS,
                               font=(self.mono, 8), anchor="e")
        baseline = y(0)
        canvas.create_line(left, baseline, right, baseline, fill=self.palette.BORDER)
        stride = (right - left) / len(self.arr)
        gap = max(2, min(7, stride * .22))
        active, pivots = set(self.current.active), set(self.current.pivot)
        settled, found = set(self.current.settled), set(self.current.found)
        colors = self._colors(self.current)
        previous = self._previous_step or self.current
        previous_colors = self._colors(previous)
        poses = bar_poses(previous.values, self.arr, self._motion_progress, self.current.swap)
        show_values = stride >= 23
        if self.current.swap and self._motion_progress < 1:
            i, j = self.current.swap
            sx, ex = left + (i + .5) * stride, left + (j + .5) * stride
            canvas.create_line(sx, top + 9, (sx + ex) / 2, 3, ex, top + 9,
                               smooth=True, fill=blend(self.palette.PANEL, self.palette.PURPLE, .5),
                               dash=(3, 4), width=2)
        for i, value in enumerate(self.arr):
            slot, visual_value, lift = poses[i]
            x0, x1 = left + slot * stride + gap / 2, left + (slot + 1) * stride - gap / 2
            end = y(visual_value)
            y0, y1 = sorted((baseline, end))
            if y1 - y0 < 3:
                y0, y1 = baseline - 3, baseline
            y0 -= lift * 18
            y1 -= lift * 18
            color = colors[i]
            if len(previous_colors) == len(colors) and self._motion_progress < 1:
                color = blend(previous_colors[i], color, ease(self._motion_progress))
            if self._finish_progress < 1 and i in settled | found:
                reveal = min(1.0, max(0.0, (self._finish_progress * 1.4 - i / len(self.arr)) * 4))
                color = blend(self.palette.ACCENT, self.palette.GREEN, reveal)
            if i in active | pivots | found:
                glow = .14 + .08 * math.sin(math.pi * self._motion_progress)
                canvas.create_rectangle(x0 - 4, y0 - 4, x1 + 4, y1 + 3,
                                        fill=blend(self.palette.PANEL, color, glow), outline="")
                canvas.create_rectangle(x0 - 1, y0 - 1, x1 + 1, y1 + 1,
                                        fill=blend(self.palette.PANEL, color, .32), outline="")
            # Layered fills create a subtle vertical gradient without images.
            for segment in range(32):
                ratio = .42 + .58 * (1 - segment / 31)
                fill = blend(self.palette.PANEL, color, ratio)
                sy0 = y0 + (y1 - y0) * segment / 32
                sy1 = y0 + (y1 - y0) * (segment + 1) / 32
                canvas.create_rectangle(x0, sy0, x1, sy1, fill=fill, outline="")
            cap = y0 if visual_value >= 0 else y1 - 2
            canvas.create_rectangle(x0, cap, x1, cap + 2, fill=color, outline="")
            if show_values:
                canvas.create_text((x0 + x1) / 2, y0 - 10 if value >= 0 else y1 + 10,
                                   text=value, fill=self.palette.TEXT if i in active | found else self.palette.MUTED,
                                   font=(self.mono, 8))
            if len(self.arr) <= 32 or i % 5 == 0:
                canvas.create_text(left + (i + .5) * stride, height - 10, text=f"{i:02}",
                                   fill=self.palette.AXIS, font=(self.mono, 7))
            self._bar_bounds.append((x0, x1, i, value))
        if self._finish_progress < 1:
            phase = self._finish_progress
            sweep = left + (right - left) * phase
            for offset in range(5):
                canvas.create_line(sweep - offset * 3, top - 8, sweep - offset * 3, bottom + 3,
                                   fill=blend(self.palette.PANEL, self.palette.GREEN, .45 - offset * .08))
            for particle in range(18):
                x = left + (right - left) * ((particle * .618) % 1)
                py = top + 8 + (particle % 4) * 10 - math.sin(phase * math.pi) * 24
                size = 1 + 2 * math.sin(phase * math.pi)
                color = blend(self.palette.PANEL, (self.palette.ACCENT, self.palette.GOLD, self.palette.PURPLE)[particle % 3], math.sin(phase * math.pi))
                canvas.create_oval(x - size, py - size, x + size, py + size, fill=color, outline="")

    def _hover(self, event):
        self.canvas.delete("tooltip")
        for x0, x1, index, value in self._bar_bounds:
            if x0 <= event.x <= x1:
                x = min(max(80, (x0 + x1) / 2), self.canvas.winfo_width() - 80)
                self.canvas.create_rectangle(x - 72, 2, x + 72, 26, fill=self.palette.BORDER,
                                             outline=self.palette.TOOLTIP_BORDER, tags="tooltip")
                self.canvas.create_text(x, 14, text=f"[{index}]  value: {value}",
                                        fill=self.palette.TEXT, font=(self.mono, 9), tags="tooltip")
                break

    def _typing(self):
        return isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox, ttk.Scale))

    def _space(self, event):
        # Button class bindings already activate focused buttons on Space.
        if not self._typing() and not isinstance(self.root.focus_get(), (tk.Button, GlassButton)):
            self.toggle_run()
            return "break"

    def _right(self, event):
        if not self._typing():
            self.step_once()
            return "break"

    def close(self):
        self._cancel()
        self._closed = True
        if self._theme_id is not None:
            self.root.after_cancel(self._theme_id)
            self._theme_id = None
        self.root.destroy()


def main():
    root = tk.Tk()
    Visualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
