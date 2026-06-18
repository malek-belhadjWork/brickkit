"""Throwaway ENGINE brick that proves the framework with no domain logic.

Prepends a configured prefix to its input string. Behavior is driven entirely
by config — the engine is never edited to change the prefix.
"""
from __future__ import annotations

from brickkit.config import BrickConfig

NAME = "echo"
VERSION = "1.0.0"
KIND = "engine"


class Config(BrickConfig):
    prefix: str = ""


CONFIG_MODEL = Config


def run(data, config):
    return f"{config.prefix}{data}"
