"""fixed locator: a ratio box mapped to pixels on the canonical page."""
from __future__ import annotations


def locate_fixed(locator, size):
    w_px, h_px = size
    x, y, bw, bh = locator.box
    return (x * w_px, y * h_px, bw * w_px, bh * h_px)
