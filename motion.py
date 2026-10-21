"""Small, deterministic motion helpers, independent of Tk and algorithm state."""

import math


def ease(progress):
    """Smoothstep: zero velocity at both ends, clamped to the unit interval."""
    progress = max(0.0, min(1.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)


def blend(start, end, progress):
    progress = max(0.0, min(1.0, progress))
    channels = [
        round(int(start[i:i + 2], 16) * (1 - progress) +
              int(end[i:i + 2], 16) * progress)
        for i in (1, 3, 5)
    ]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def bar_poses(previous, current, progress, swap=()):
    """Return (slot, height, lift) for each destination bar.

    A swap carries each bar at its actual height along an elevated path.
    Buffer writes ease heights without changing the immutable algorithm values.
    Lift is normalized; the renderer scales it to available chart space.
    """
    amount = ease(progress)
    valid_swap = (len(swap) == 2 and len(previous) == len(current)
                  and swap[0] != swap[1]
                  and all(0 <= index < len(current) for index in swap))
    poses = []
    for index, value in enumerate(current):
        if valid_swap and index in swap:
            source = swap[1] if index == swap[0] else swap[0]
            slot = source + (index - source) * amount
            lift = math.sin(math.pi * amount) * (1.0 if index == swap[0] else .45)
            poses.append((slot, float(value), lift))
        else:
            before = previous[index] if len(previous) == len(current) else value
            poses.append((float(index), before + (value - before) * amount, 0.0))
    return poses
