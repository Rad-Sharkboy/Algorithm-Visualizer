# Algorithm Visualizer (Python + Tkinter)

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-purple?style=flat-square)
![Status](https://img.shields.io/badge/Status-Work_In_Progress-orange?style=flat-square)

A lightweight, interactive tool I threw together to visualize how sorting and searching algorithms actually work under the hood. I built this because reading about O(n²) is one thing, but actually *watching* the bars move makes it click in the brain and easy to remember.

It’s currently a mini-project/prototype, but it handles the basics!

## 📸 Preview

*(screenshot or GIF here to add)*

## 🚀 Features

* **Zero Dependencies:** Runs entirely on the Python standard library (`tkinter`, `random`, `time`). No `pip install` needed.
* **Real-time Visualization:** Visualizes the comparison and swapping steps with a delay so you can follow the logic.
* **Color Coded:**
    * 🟨 **Yellow:** Default elements.
    * 🟥 **Red:** Elements currently being compared or swapped.
    * 🟩 **Green:** Element found (Linear Search).

### Implemented Algorithms
1.  **Bubble Sort:** The classic sinking sort.
2.  **Selection Sort:** Scans for the minimum and swaps it to the front.
3.  **Linear Search:** Iterates through the list to find a specific number.

## 🛠️ How to Run

Since there are no external libraries, you just need Python installed.

1.  Clone the repo:
    ```bash
    git clone [https://github.com/yourusername/algo-visualizer.git](https://github.com/yourusername/algo-visualizer.git)
    ```
2.  Navigate to the directory:
    ```bash
    cd algo-visualizer
    ```
3.  Run the script:
    ```bash
    python main.py
    ```

## Known Bugs

* **Hardcoded Search:** The "Linear Search" button currently only looks for the number `50`. If `50` wasn't generated in the random array, it just searches to the end and does nothing.
* **No "Stop" Button:** Once you start a sort, you have to let it finish. If you try to close the window mid-sort, it might throw an error in the console.
* **Visual Artifacts:** If you click a sort button *while* another sort is already running, the canvas `delete("all")` fights with the previous loop, causing the bars to flicker or disappear.
* **No Promts:** Right now when the Algorithm finishes it doesnt give a "Done" or "Found!" Message/Promt.

## 📝 To-Do List

This is a WIP, so there is a lot I want to add:

- [ ] **Dynamic Search:** Add an Input Box so the user can type in *which* number they want to find.
- [ ] **Reset Button:** Currently, you have to restart the app to generate a new random array.
- [ ] **Add Merge Sort & Quick Sort:** These are harder to visualize recursively, but working on it.
- [ ] **Speed Control:** Add a slider to adjust the `delay` variable (speed up or slow down execution).
- [ ] **Better Colors:** Make the bars turn Green as they reach their final sorted position, Aswell as make the buttons more Visually appealing.

This is just a side project to learn Tkinter and Algorithms, but if you know how to fix the threading issue or want to add a new algorithm, feel free to fork it and open a Pull Request!
