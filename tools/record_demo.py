"""Record the current console demo for the README (X11 + FFmpeg)."""

import argparse
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_console_preview import record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs")
    output = parser.parse_args().output.resolve()
    record(output)
    shutil.copyfile(output / "maroon.png", output / "preview.png")


if __name__ == "__main__":
    main()
