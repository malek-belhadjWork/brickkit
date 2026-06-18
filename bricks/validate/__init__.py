"""validate — engine+config brick. Required fields + confidence + cross-field
checks -> {ok, flags}. KIND=engine."""
from __future__ import annotations

from .config_model import Config
from .engine import run

NAME = "validate"
VERSION = "1.0.0"
KIND = "engine"
CONFIG_MODEL = Config

__all__ = ["NAME", "VERSION", "KIND", "CONFIG_MODEL", "run"]
