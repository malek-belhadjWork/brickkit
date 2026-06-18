"""writeout — engine+config brick. Write records to a destination with a
field->column mapping. KIND=engine."""
from __future__ import annotations

from .config_model import Config
from .engine import run

NAME = "writeout"
VERSION = "1.0.0"
KIND = "engine"
CONFIG_MODEL = Config

__all__ = ["NAME", "VERSION", "KIND", "CONFIG_MODEL", "run"]
