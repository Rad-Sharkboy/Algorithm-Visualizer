"""Record the real Tk app as a looping README GIF (Linux/X11 + FFmpeg)."""

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PROJECT import Visualizer  # noqa: E402


def record(output):
    if not shutil.which("ffmpeg"):
        raise SystemExit("Install FFmpeg to record the demo.")
    if not os.environ.get("DISPLAY"):
        raise SystemExit("Set DISPLAY to a working X11 display.")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="algo-demo-") as temporary:
        video = Path(temporary) / "demo.mp4"
        log = Path(temporary) / "ffmpeg.log"
        root = tk.Tk()
        app = Visualizer(root)
        app.theme_var.set("Dark")
        app._change_theme()
        root.geometry(f"{min(1280, root.winfo_screenwidth())}x"
                      f"{min(860, root.winfo_screenheight())}+0+0")
        app._select_algorithm("Comb Sort")
        app.set_data([76, 21, 60, 12, 91, 43, 9, 68])
        app.speed_var.set(35)
        app._speed_changed()
        root.update()
        root.lift()
        errors = []
        completed = []

        def callback_error(*error):
            errors.append(str(error[1]))
            root.quit()

        root.report_callback_exception = callback_error

        def finish():
            completed.append(True)
            root.quit()

        stages = [
            ("Shell Sort", [91, 12, 68, 21, 76, 9, 60, 43], 45, "Light"),
            ("Interpolation Search", [-30, 20, 15, 90, 0, -15, 20, 60, -10, 30, 75, -5], 25, "Dark"),
        ]

        def next_stage():
            if not stages:
                finish()
                return
            name, values, speed, appearance = stages.pop(0)
            app.theme_var.set(appearance)
            app._change_theme()
            app._select_algorithm(name)
            app.set_data(values)
            app.target_var.set("60")
            app.speed_var.set(speed)
            app._speed_changed()
            root.after(650, start)

        def check_completion():
            if app.state == "done":
                root.after(1100, next_stage)
            else:
                root.after(30, check_completion)

        def start():
            app.run_button.event_generate("<Enter>")
            app.run_button.invoke()
            root.after(700, lambda: app.run_button.event_generate("<Leave>"))
            check_completion()

        with log.open("w") as diagnostics:
            recorder = subprocess.Popen([
                "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
                "-f", "x11grab", "-window_id", str(root.winfo_id()),
                "-draw_mouse", "0", "-framerate", "24", "-i", os.environ["DISPLAY"],
                "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", str(video),
            ], stdout=subprocess.DEVNULL, stderr=diagnostics)
            try:
                root.after(900, start)
                root.after(45000, root.quit)
                root.mainloop()
            finally:
                if recorder.poll() is None:
                    recorder.send_signal(signal.SIGINT)
                recorder.wait(timeout=10)
                app.close()
        if errors or not completed or recorder.returncode not in (0, 255):
            raise RuntimeError(f"Recording failed: {errors or log.read_text() or 'demo timed out'}")

        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-threads", "2",
            "-i", str(video), "-filter_complex_threads", "1",
            "-filter_complex",
            "fps=20,scale=1000:-2:flags=lanczos,split[a][b];"
            "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
            "-loop", "0", str(output / "demo.gif"),
        ], check=True)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", str(video),
            "-frames:v", "1", "-threads", "1", str(output / "preview.png"),
        ], check=True)
        print(f"Saved {output / 'demo.gif'} and {output / 'preview.png'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs")
    record(parser.parse_args().output.resolve())
