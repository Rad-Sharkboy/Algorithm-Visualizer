<div align="center">

# ⚡ ALGO STUDIO

### Algorithms have moves. Now you can see them. 🪄

**A tiny Python playground with a big personality.**<br>
Turn “wait, how does that work?” into “ohhh, I get it.”

<img alt="Python 3.10 or newer" src="https://img.shields.io/badge/Python-3.10%2B-56e0bf?style=for-the-badge&logo=python&logoColor=0a101c" />
<img alt="13 algorithms" src="https://img.shields.io/badge/13-ALGORITHMS-b09aff?style=for-the-badge" />
<img alt="No pip dependencies" src="https://img.shields.io/badge/PIP_INSTALLS-ZERO-f5c773?style=for-the-badge" />
<img alt="Light, Dark, and System themes" src="https://img.shields.io/badge/THEMES-LIGHT_%C2%B7_DARK_%C2%B7_AUTO-75a8e8?style=for-the-badge" />

[🎮 Press play](#press-play) · [🧠 Meet the algorithms](#the-lineup) · [🎛️ Take control](#the-controls) · [🧪 Try a challenge](#challenge-mode)

</div>

![Live Algo Studio demo showing frosted playback controls, rounded sliders, and sorting and searching in dark and light themes](docs/demo.gif)

<p align="center"><sub>🎬 Actual app footage. Sorting, searching, and playback controls in Dark and Light themes.</sub></p>

---

## ✨ Visualize each step

| Playback | Inspection | Customization |
| :--- | :--- | :--- |
| Animated swaps, value writes, and completion highlights make each operation visible. | Track comparisons, array writes, highlighted pseudocode, and an explanation of every step. | Enter custom arrays, choose from four presets, adjust playback speed, and set search targets. |
| Pause, resume, or advance one step at a time. | Hover over a bar to inspect its index and value. | Light, Dark, and System themes, with optional Reduced motion. |

Stopping a run restores the original array. Negative integers, zeros, and duplicate values are supported.

> **[v2.1.3 · Frost](https://github.com/Rad-Sharkboy/Algorithm-Visualizer/releases/tag/v2.1.3)** introduces rounded playback controls, softly shaded surfaces, and sliders with precise mouse and keyboard input.

<details>
<summary><strong>🌓 Appearance and accessibility</strong></summary>

<br>

| Light | Dark | System |
| :--- | :--- | :--- |
| Pale surfaces, dark text, and clear accent colors. | Dark panels with restrained highlights. | Follows Windows' app color preference, including changes while the app is open. |

Choose **System / Light / Dark** beside the title. Windows changes are detected within about two seconds. On other systems, or when the preference cannot be read, System uses Dark. Switching themes preserves playback, input, focus, and open guides.

The **Run / Pause / Resume / Replay** button uses a rounded frosted surface, a clear icon, and a subtle press transition. The **animation speed** and **array size** sliders use rounded tracks and raised capsule handles. Click a track, drag a handle, or use the keyboard for precise adjustment.

Focused controls have a visible outline. **Reduced motion** disables decorative transitions while preserving playback and single-step inspection. Button and slider effects settle after interaction rather than animating continuously.

**Native fonts:** Segoe UI Variable / Segoe UI on Windows, SF Pro Text / Helvetica Neue when available on macOS, and Noto Sans / DejaVu Sans elsewhere. Code and values use installed fonts such as Cascadia, Consolas, or Menlo, with system fallbacks. No font downloads are required.

<sub>Frosted shading and rounded controls are rendered in Tkinter using the Python standard library.</sub>

</details>

<a id="press-play"></a>

## 🎮 Getting started

Requires **Python 3.10+**, **Tkinter**, and a graphical desktop. No pip dependencies are required.

```bash
git clone https://github.com/Rad-Sharkboy/Algorithm-Visualizer.git
cd Algorithm-Visualizer
python3 PROJECT.py
```

On Windows, use `py PROJECT.py`. To check whether Tkinter is available, run `python3 -m tkinter`; a small demonstration window should open.

**Select an algorithm → configure the input → press Run → inspect each step.**

<a id="the-lineup"></a>

## 🧠 Algorithm library

### Sorting

| Algorithm | Approach |
| :--- | :--- |
| 🫧 **Bubble Sort** | Compare adjacent values and swap pairs that are out of order. |
| 🎯 **Selection Sort** | Select the minimum remaining value and place it at the next position. |
| 🃏 **Insertion Sort** | Insert each value into the sorted portion of the array. |
| 🐚 **Shell Sort** | Apply insertion sort across progressively smaller gaps. |
| 🪮 **Comb Sort** | Compare and swap values separated by a shrinking gap. |
| 🧩 **Merge Sort** | Recursively sort two halves, then merge them. |
| ⚡ **Quick Sort** | Partition around a pivot and recursively sort each side. |
| 🏔️ **Heap Sort** | Build a max heap and repeatedly extract its largest value. |
| 🧮 **Counting Sort** | Count integer frequencies, then reconstruct the sorted array. |
| 📬 **Radix Sort** | Process digits from least to most significant with stable counting passes. |

### Searching

| Algorithm | Approach |
| :--- | :--- |
| 🚶 **Linear Search** | Check each value in sequence until a match is found. |
| ✂️ **Binary Search** | Repeatedly halve the search interval in a sorted array. |
| 📍 **Interpolation Search** | Estimate the target position using the values at the interval boundaries. |

> 📌 **Search rules:** indices start at zero. Linear Search returns the **first matching index**. Binary and Interpolation Search stop at the match they encounter; with duplicates, that may be a later occurrence. They sort a copy first, so their result indices refer to that sorted copy. The app tells you when it does this. Reset restores your original order.

<details>
<summary><strong>📊 Complexity and implementation details</strong></summary>

<br>

| Algorithm | Average time | Worst time | Extra space |
| :--- | :---: | :---: | :---: |
| Bubble Sort | O(n²) | O(n²) | O(1) |
| Selection Sort | O(n²) | O(n²) | O(1) |
| Insertion Sort | O(n²) | O(n²) | O(1) |
| Shell Sort | Gap-dependent | O(n²) | O(1) |
| Comb Sort | Gap-dependent | O(n²) | O(1) |
| Merge Sort | O(n log n) | O(n log n) | O(n) |
| Quick Sort | O(n log n) | O(n²) | O(n) |
| Heap Sort | O(n log n) | O(n log n) | O(1) |
| Counting Sort | O(n + k) | O(n + k) | O(k) |
| Radix Sort | O(d · n) | O(d · n) | O(n) |
| Linear Search | O(n) | O(n) | O(1) |
| Binary Search | O(log n) | O(log n) | O(1) |
| Interpolation Search | O(log log n)* | O(n) | O(1) |

- **n** = number of values, **k** = integer range, **d** = base-10 digit count.
- **Shell** uses the original halving gaps: `n // 2, …, 1`. **Comb** shrinks its gap by 1.3 and finishes only after a gap-1 pass makes no swaps.
- **Selection** performs its two array assignments every pass, even when the minimum is already in place; these still count as writes.
- **Quick** uses the final value as pivot, scans inward from both sides, and recursively sorts the partitions. **Merge** recursively splits the array, then joins halves using two temporary arrays.
- **Radix** uses ten digit counts, cumulative totals, and a right-to-left output pass before copying back. Each pass multiplies the digit place by ten. Negative keys use an offset; **Counting** also supports negative integers.
- **Interpolation's average** assumes uniformly distributed, distinct keys. Skewed data can take linear time. Equal endpoints are handled without dividing by zero.
- Costs above describe the algorithms. Copying visual frames, storing the original input, and drawing the chart add overhead. Sorting a search input is preparation, excluded from search comparison/write counts.

</details>

<a id="the-controls"></a>

## 🎛️ Playback and input controls

| Control | Action |
| :--- | :--- |
| ▶️ **Run / Pause / Resume** | Start, pause, or continue playback. |
| 👣 **Step** | Inspect one exact algorithm snapshot at a time. |
| 🛑 **Stop** | Cancel playback and restore the original input. |
| ↩️ **Reset** | Restore the original input and clear the counters. |
| 🔁 **Replay** | Run the algorithm again on the original array. |
| 🎲 **Generate** | Create random, nearly sorted, reversed, or few-unique-value arrays. |
| ✍️ **Apply** | Use your own comma- or space-separated integers. |
| 🏎️ **Animation speed** | Adjust playback speed, including while an algorithm is running. |
| **Array size** | Choose 8–64 values for the next generated array, then press Generate. |
| 🌙 **Reduced motion** | Disable decorative transitions while retaining every algorithm step. |
| 🌓 **Theme** | Choose Light, Dark, or the Windows-following System mode without interrupting playback. |
| 📖 **Algorithm guide** | Open the explanation, pseudocode, and complexity. |

**Input limits:** generated arrays have **8–64 values**. Custom arrays accept **1–64 integers from −999 to 999**. Hover over any bar for its index and exact value.

<details>
<summary><strong>⌨️ Keyboard shortcuts</strong></summary>

<br>

| Key | Action |
| :---: | :--- |
| <kbd>Space</kbd> | Run / Pause / Resume |
| <kbd>→</kbd> | Next step |
| <kbd>Esc</kbd> | Stop |
| <kbd>Ctrl</kbd> + <kbd>R</kbd> | Reset |
| <kbd>Enter</kbd> in **Your Data** | Apply the array |
| <kbd>Enter</kbd> in **Target** | Run the search |

Typing and cursor movement work normally in input fields. Focused buttons support Space and Enter. A focused slider uses arrow keys for one-unit adjustments, Page Up / Page Down for ten units, and Home / End for its limits; these keys do not advance the algorithm.

</details>

<details>
<summary><strong>🎨 Color guide and metrics</strong></summary>

<br>

| Color | Meaning |
| :--- | :--- |
| 🩵 Teal | Unvisited |
| 💜 Purple | Being compared or written |
| 💛 Amber | Pivot or search boundary |
| 💚 Green | Settled value or search match |
| 🩶 Muted gray | Eliminated search position |

Each step includes a text description. Search results and sort completion are reported explicitly.

- **Comparisons:** value comparisons made by the algorithm.
- **Array writes:** assignments to the main array; a swap counts as two. Auxiliary buffers and buckets are excluded.
- **Visual steps:** displayed algorithm snapshots, including explanation and completion frames. Animation in-between frames do not inflate this count.
- **Active time:** animation time excluding pauses. This measures visualization time rather than algorithm execution performance.

</details>

<a id="challenge-mode"></a>

## 🧪 Examples to explore

| Example | Procedure |
| :--- | :--- |
| 🪮 **Comb Sort gaps** | Paste `76, 21, 60, 12, 91, 43, 9, 68`, choose **Comb Sort**, and watch distant bars trade places. |
| 🐚 **Shell Sort passes** | Replay that same input with **Shell Sort**. Spot the moment the gap becomes 1. |
| 👯 **Duplicate search values** | Paste `9, -4, 9, 0, -4, 12`, search for `-4`, and compare Linear with Interpolation. Why are the indices different? |
| 🫧 **Input order and comparisons** | Generate a nearly sorted array. Compare Bubble's counts with a reversed input of the same size. |
| 🧊 **Inspect a merge** | Pause a merge, press Step, and explain the next write before it happens. |

<details>
<summary><strong>🛠️ Project structure</strong></summary>

<br>

```text
Algo Studio
├── PROJECT.py          🎛️ Interface + animation controller
├── algorithms.py       🧠 13 incremental algorithms
├── motion.py           Easing, colors + swap trajectories
├── datasets.py         🎲 Presets + input validation
├── theme.py            🎨 Palette, fonts + widget styling
├── docs/               🎬 The actual app demo
├── widgets.py          Frosted controls + sliders
└── tools/record_demo.py 📹 Demo recorder
```

Tk's event loop keeps animations responsive without worker threads or blocking sleeps. Changing data, switching algorithms, resetting, or closing the window cancels pending callbacks. Stop restores the original values because shifting and merging can temporarily overwrite array positions.

Pausing settles the current visual transition. Single-step shows an exact snapshot. Very fast playback skips transitions to keep up; reduced motion disables transitions and completion effects entirely.

The layout supports windows from **1000 × 740**. On shorter windows, inline notes are hidden; **Algorithm guide** stays available. Importing the modules does not launch the app.

</details>

---

<div align="center">

### Explore the algorithm. Inspect each step.

A focused environment for understanding sorting and searching.

</div>
