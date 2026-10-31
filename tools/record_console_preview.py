"""Record the console preview into a temporary folder, without changing README media.

Requires an X11 display and FFmpeg for capture; the app itself has no dependencies.
Usage: python3 tools/record_console_preview.py --output temp/oscilloscope-preview
"""

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PROJECT import Visualizer


def record(output):
    if not shutil.which("ffmpeg") or not os.environ.get("DISPLAY"):
        raise SystemExit("Recording needs FFmpeg and a working X11 DISPLAY.")
    output.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    app = Visualizer(root)
    root.geometry("1280x900+0+0")
    app.theme_var.set("Maroon")
    app._change_theme()
    app._select_algorithm("Quick Sort")
    app.set_data([76, 21, 60, 12, 91, 43, 9, 68, 35, 82, 18, 57])
    app.speed_var.set(30)
    app.manager.finish_tweens()
    app.title.progress = 0
    app.algorithm_list.intro = [0.0] * 13
    for row in app.canvas.display.values():
        row[1] = 0
    root.update()
    app.title.paint()
    app.algorithm_list.paint()
    app.canvas.paint()
    root.lift()
    errors, completed, marks = [], [], {}
    began = time.perf_counter()
    later = app.manager.call_later

    def fail(*error):
        errors.append(str(error[1]))
        root.quit()

    root.report_callback_exception = fail

    def mark(name):
        marks[name] = time.perf_counter() - began

    def click(widget):
        x, y = widget.winfo_width() // 2, widget.winfo_height() // 2
        widget.event_generate("<Enter>")
        widget.event_generate("<ButtonPress-1>", x=x, y=y)
        later(90, lambda: widget.event_generate("<ButtonRelease-1>", x=x, y=y))
        later(250, lambda: widget.event_generate("<Leave>"))

    def watch(next_stage):
        if app.state == "done" and not app._completing:
            later(1100, next_stage)
        else:
            later(40, lambda: watch(next_stage))

    def slider_to(slider, value):
        left, right, center = slider._geometry()
        destination = left + (right - left) * (value - slider.minimum) / (slider.maximum - slider.minimum)
        slider.event_generate("<Enter>")
        slider.event_generate("<ButtonPress-1>", x=round(center), y=13)
        for step in range(1, 11):
            x = round(center + (destination - center) * step / 10)
            later(step * 40, lambda position=x: slider.event_generate("<B1-Motion>", x=position, y=13))
        later(440, lambda: slider.event_generate("<ButtonRelease-1>", x=round(destination), y=13))
        later(520, lambda: slider.event_generate("<Leave>"))

    def pause_and_adjust():
        click(app.run_button)
        later(300, lambda: slider_to(app.speed_scale, 42))
        later(1400, lambda: click(app.run_button))

    def choose_theme(name):
        app.theme_box.invoke()
        def choose():
            app.theme_box._choice = app.theme_box.values.index(name)
            app.theme_box._choose()
        later(350, choose)

    def start_primary():
        click(app.run_button)
        later(1400, lambda: mark("maroon"))
        later(1800, pause_and_adjust)
        later(3300, lambda: choose_theme("Red"))
        later(4200, lambda: mark("red"))
        later(6200, lambda: choose_theme("Purple"))
        later(7100, lambda: mark("purple"))
        watch(start_paper)

    def start_paper():
        mark("paper_transition")
        app.theme_box.invoke()
        def choose_paper():
            app.theme_box._choice = app.theme_box.values.index("Light")
            app.theme_box._choose()
            nav = app.algorithm_list
            row = nav.names.index("Shell Sort")
            nav.event_generate("<Motion>", x=65, y=row * 30 + 20)
            later(400, lambda: nav.event_generate("<ButtonRelease-1>", x=65, y=row * 30 + 20))
            later(500, prepare_paper)
        later(500, choose_paper)

    def prepare_paper():
        app.algorithm_list.event_generate("<Leave>")
        app.set_data([91, 12, 68, 21, 76, 9, 60, 43])
        slider_to(app.speed_scale, 50)
        later(700, lambda: click(app.run_button))
        later(2300, lambda: mark("paper"))
        watch(start_search)

    def start_search():
        mark("search")
        app._select_algorithm("Binary Search")
        choose_theme("Dark")
        later(650, prepare_search)

    def prepare_search():
        app.custom_var.set("-30, 20, 15, 90, 0, 60, 30, 75")
        app.target_var.set("60")
        slider_to(app.speed_scale, 10)
        later(500, lambda: click(app.apply_button))
        def run_search():
            if app.original != [-30, 20, 15, 90, 0, 60, 30, 75]:
                raise RuntimeError("The search preview input was not applied")
            click(app.run_button)
        later(1100, run_search)
        later(2500, lambda: mark("phosphor"))
        later(1200, lambda: watch(reduced_motion))

    def reduced_motion():
        mark("reduced_motion")
        click(app.motion_toggle)
        later(500, lambda: click(app.reset_button))
        later(1000, lambda: click(app.run_button))
        later(1200, lambda: watch(interrupt_preview))

    def interrupt_preview():
        click(app.motion_toggle)
        app._select_algorithm("Comb Sort")
        app.set_data([91, 43, 9, 68, 35, 82, 18, 57])
        app.speed_var.set(32)
        app.theme_var.set("Maroon")
        app._change_theme()
        later(500, lambda: click(app.run_button))
        later(1800, lambda: click(app.reset_button))
        later(2400, finish)

    def finish():
        completed.append(True)
        root.quit()

    video = output / "demo.mp4"
    with tempfile.TemporaryDirectory(prefix="algo-console-") as temporary:
        log = Path(temporary) / "capture.log"
        with log.open("w") as diagnostics:
            recorder = subprocess.Popen([
                "ffmpeg", "-y", "-loglevel", "error", "-nostdin", "-f", "x11grab",
                "-window_id", str(root.winfo_id()), "-draw_mouse", "0", "-framerate", "60",
                "-i", os.environ["DISPLAY"], "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", str(video),
            ], stdout=subprocess.DEVNULL, stderr=diagnostics)
            try:
                later(600, app._launch)
                later(2000, start_primary)
                later(55000, root.quit)
                root.mainloop()
            finally:
                if recorder.poll() is None:
                    recorder.send_signal(signal.SIGINT)
                recorder.wait(timeout=10)
                app.close()
        if errors or not completed or recorder.returncode not in (0, 255):
            raise RuntimeError(f"Capture failed: {errors or log.read_text() or 'timed out'}")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-threads", "2", "-i", str(video),
            "-filter_complex_threads", "1", "-filter_complex",
            "fps=18,scale=1000:-2:flags=lanczos,split[a][b];"
            "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
            "-loop", "0", str(output / "demo.gif"),
        ], check=True)
        for name in ("red", "maroon", "purple", "phosphor", "paper"):
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-ss", str(marks[name]), "-i", str(video),
                "-frames:v", "1", "-threads", "1", str(output / f"{name}.png"),
            ], check=True)
    print(f"Saved actual app footage to {output}")
    print("Scene markers:", {name: round(value, 1) for name, value in marks.items()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "temp" / "oscilloscope-preview")
    record(parser.parse_args().output.resolve())
