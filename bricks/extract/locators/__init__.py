"""Locator strategy: turn a field's locator config into a pixel box on the
(canonical-resolution) page. The dispatch is the seam that lets new locator
kinds (e.g. `anchor`) drop in without touching cropping or reconciliation."""
from __future__ import annotations


def locate(locator, size: tuple[int, int]) -> tuple[float, float, float, float]:
    """Return (x, y, w, h) in pixels for the given locator and page size."""
    if locator.kind == "fixed":
        from .fixed import locate_fixed

        return locate_fixed(locator, size)
    raise ValueError(f"unknown locator kind {locator.kind!r}")
