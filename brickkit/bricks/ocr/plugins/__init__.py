"""Explicitly import each plugin so its @REGISTRY.register decorator fires."""
from __future__ import annotations

from . import cloud, synthetic, tesseract  # noqa: F401
