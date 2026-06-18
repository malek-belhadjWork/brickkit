"""The ocr brick's own plugin registry."""
from __future__ import annotations

from brickkit.registry import Registry

# Stable interface: a built plugin is callable (image) -> (text, confidence),
# where image is a PIL.Image crop and confidence is normalized to 0..1.
REGISTRY = Registry(interface="(image) -> (text: str, confidence: float in 0..1)")
