"""Input validation and reproducible dataset presets, independent of the GUI."""

import random
import re


def parse_values(text):
    """Accept comma/whitespace-separated bounded integers without partial parses."""
    pieces = [part for part in re.split(r"[\s,]+", text.strip()) if part]
    if not pieces:
        raise ValueError("Enter at least one integer.")
    if len(pieces) > 64:
        raise ValueError("Use at most 64 values so every bar stays visible.")
    try:
        values = [int(part) for part in pieces]
    except ValueError:
        raise ValueError("Use whole numbers separated by commas or spaces.") from None
    if any(value < -999 or value > 999 for value in values):
        raise ValueError("Keep values between −999 and 999.")
    return values


def generate_values(size, preset="Random", rng=None):
    """Generate 8–64 values; an optional Random instance makes demos repeatable."""
    rng = rng or random
    size = max(8, min(64, round(size)))
    values = [rng.randint(10, 99) for _ in range(size)]
    if preset == "Nearly sorted":
        values.sort()
        for _ in range(max(1, size // 10)):
            left, right = rng.sample(range(size), 2)
            values[left], values[right] = values[right], values[left]
    elif preset == "Reversed":
        values.sort(reverse=True)
    elif preset == "Few unique":
        choices = rng.sample(range(10, 100), 4)
        values = [rng.choice(choices) for _ in range(size)]
    elif preset != "Random":
        raise ValueError(f"Unknown dataset preset: {preset}")
    return values
