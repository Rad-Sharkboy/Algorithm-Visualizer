"""Cached, anti-aliased control sprites rendered with the standard library."""

import base64
from collections import OrderedDict
import math
import struct
import zlib


def _aa_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _aa_clamp01(value):
    return max(0.0, min(1.0, value))


def _aa_png(width, height, rows):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def _aa_rounded_sdf(x, y, cx, cy, hx, hy, radius):
    qx, qy = abs(x - cx) - (hx - radius), abs(y - cy) - (hy - radius)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - radius


def render_box(w, h, radius, fill, border=None, border_w=1.0, fill_bottom=None,
               corners=(True, True, True, True), shadow=0.0, shadow_dy=1.0, shadow_blur=2.0):
    """Return PNG bytes; sizes are physical pixels, including any shadow padding."""
    if any(not isinstance(size, int) or isinstance(size, bool) or size < 1 for size in (w, h)):
        raise ValueError("Sprite dimensions must be positive integers.")
    if len(corners) != 4:
        raise ValueError("Provide four corner flags.")
    if border_w < 0 or not 0 <= shadow <= 1 or (shadow and shadow_blur <= 0):
        raise ValueError("Invalid border width or shadow parameters.")
    top, bottom = _aa_rgb(fill), _aa_rgb(fill_bottom or fill)
    edge = _aa_rgb(border) if border else None
    cx, cy, hx, hy = w / 2, h / 2, w / 2, h / 2
    pad = shadow_blur + shadow_dy if shadow else 0
    if shadow:
        hx, hy = hx - pad, hy - pad
        if min(hx, hy) <= 0:
            raise ValueError("Sprite dimensions must leave room for the shadow padding.")
        radius = max(0.0, radius - pad)
    radius = max(0.0, min(radius, hx, hy))
    rounded = all(corners)
    mirror = corners[0] == corners[1] and corners[3] == corners[2]
    margin = pad + radius + border_w + (shadow_blur + abs(shadow_dy) if shadow else 0) + 1
    side = min(w // 2, max(0, math.ceil(margin)))
    span = w - 2 * side
    rows = []
    for py in range(h):
        y = py + 0.5
        t = _aa_clamp01((y - (cy - hy)) / max(1.0, 2 * hy))
        base = tuple(top[i] + (bottom[i] - top[i]) * t for i in range(3))

        def pixel(px):
            x = px + 0.5
            r = radius
            if not rounded:
                left, upper = x < cx, y < cy
                index = 0 if left and upper else 1 if upper else 3 if left else 2
                r = radius if corners[index] else 0.0
            d = _aa_rounded_sdf(x, y, cx, cy, hx, hy, r)
            outer = _aa_clamp01(0.5 - d)
            inner = _aa_clamp01(0.5 - (d + border_w)) if edge else outer
            ring = outer - inner
            alpha, color = outer, base
            if edge and outer > 0:
                color = tuple((base[i] * inner + edge[i] * ring) / outer for i in range(3))
            if shadow:
                distance = _aa_rounded_sdf(x, y - shadow_dy, cx, cy, hx, hy, r)
                shaded = _aa_clamp01(0.5 - distance / shadow_blur) * shadow * (1 - alpha)
                total = alpha + shaded
                if total > 0:
                    color = tuple(value * alpha / total for value in color)
                alpha = total
            return bytes((round(color[0]), round(color[1]), round(color[2]), round(alpha * 255)))

        left = [pixel(px) for px in range(side)]
        middle = pixel(side) * span if span else b""
        right = reversed(left) if mirror else (pixel(px) for px in range(w - side, w))
        rows.append(b"".join(left) + middle + b"".join(right))
    return _aa_png(w, h, rows)


def render_corner_mask(radius, color, corner="tl"):
    """Paint outside a rounded corner in the background color, with an alpha edge."""
    if corner not in ("tl", "tr", "bl", "br") or not math.isfinite(radius) or radius < 0:
        raise ValueError("Use a nonnegative radius and tl, tr, bl, or br.")
    size, rgb = max(1, math.ceil(radius)), _aa_rgb(color)
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            x = px + 0.5 if corner in ("tl", "bl") else size - (px + 0.5)
            y = py + 0.5 if corner in ("tl", "tr") else size - (py + 0.5)
            inside = x < radius and y < radius
            distance = math.hypot(radius - x, radius - y) - radius if inside else -1
            alpha = _aa_clamp01(0.5 + distance) if inside else 0.0
            row += bytes((*rgb, round(alpha * 255)))
        rows.append(bytes(row))
    return _aa_png(size, size, rows)


class SpriteCache:
    """Bounded per-root LRU; widgets must also retain their displayed PhotoImages."""

    def __init__(self, root, limit=256):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("Sprite cache limit must be a positive integer.")
        self.root, self.limit, self._images = root, limit, OrderedDict()

    def get(self, kind, *args, **kwargs):
        if "corners" in kwargs:
            kwargs["corners"] = tuple(kwargs["corners"])
        key = (kind, args, tuple(sorted(kwargs.items())))
        image = self._images.get(key)
        if image is None:
            import tkinter as tk
            data = {"box": render_box, "corner": render_corner_mask}[kind](*args, **kwargs)
            image = tk.PhotoImage(master=self.root, data=base64.b64encode(data))
            self._images[key] = image
            while len(self._images) > self.limit:
                self._images.popitem(last=False)
        else:
            self._images.move_to_end(key)
        return image

    def box(self, *args, **kwargs):
        return self.get("box", *args, **kwargs)

    def corner(self, *args, **kwargs):
        return self.get("corner", *args, **kwargs)
