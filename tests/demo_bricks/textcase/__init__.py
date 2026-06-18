"""Throwaway REGISTRY brick that proves the plugin convention.

Stable interface: ``(text: str) -> str``. Plugins ``upper`` and ``lower`` are
interchangeable; config picks one via ``impl``. Adding a new case transform is a
new plugin file only — this engine never changes.
"""
from __future__ import annotations

from brickkit.config import RegistryConfig
from brickkit.registry import Registry

NAME = "textcase"
VERSION = "1.0.0"
KIND = "registry"

REGISTRY = Registry(interface="(text: str) -> str")


class Config(RegistryConfig):
    pass


CONFIG_MODEL = Config

# Explicit plugin imports register the implementations (deterministic, visible).
from . import plugins  # noqa: E402,F401


def run(data, config):
    plugin = REGISTRY.create(config.impl, config.params)
    return plugin(data)
