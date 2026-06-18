"""ocr — registry brick. image crop -> (text, confidence). KIND=registry.

Plugins: tesseract (real, deferred import), synthetic (dependency-free template
matcher used when no OCR engine is installed), cloud (stub). Config selects one
via `impl`. This brick is normally injected into `extract` (called per crop),
not run as a standalone pipeline stage.
"""
from __future__ import annotations

from .config_model import Config
from .registry import REGISTRY

NAME = "ocr"
VERSION = "1.0.0"
KIND = "registry"
CONFIG_MODEL = Config

from . import plugins  # noqa: E402,F401


def run(data, config):
    """Standalone use: OCR a single image. `data` is a PIL.Image."""
    plugin = REGISTRY.create(config.impl, config.params)
    return plugin(data)
