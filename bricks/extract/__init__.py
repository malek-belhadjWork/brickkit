"""extract — engine+config brick. Zonal/template OCR with reconciliation.

KIND=engine. Depends on the `ocr` brick, injected per the framework convention
(INJECTS) so the engine keeps the pure run(input, config) shape and calls
config.ocr(crop) per region.
"""
from __future__ import annotations

from .config_model import Config
from .engine import run

NAME = "extract"
VERSION = "1.0.0"
KIND = "engine"
CONFIG_MODEL = Config

# Bind the built `ocr` plugin onto config.ocr at wiring time.
INJECTS = {"ocr": "ocr"}

__all__ = ["NAME", "VERSION", "KIND", "CONFIG_MODEL", "INJECTS", "run"]
