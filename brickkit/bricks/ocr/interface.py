"""Stable interface for the `ocr` registry brick.

An OCR plugin reads an image crop and returns recognized text + confidence:

    run(image) -> (text: str, confidence: float)   # confidence normalized 0..1

`image` is a PIL.Image (a crop produced by the extract brick). Plugins normalize
their native confidence to 0..1 so reconciliation can compare across engines.

New OCR engines are added as new plugins only; this signature never changes.
"""
from __future__ import annotations

from typing import Protocol


class OCRPlugin(Protocol):
    def __call__(self, image) -> tuple[str, float]: ...
