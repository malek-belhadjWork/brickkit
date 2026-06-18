"""brickkit — the reusable core for building modular "bricks".

A *brick* = a generic ENGINE (core logic, never edited per client) + a CONFIG
(the only client/instance-specific surface). Every engine has the shape
``run(input, config) -> output`` so bricks compose into pipelines.

Two kinds of brick:
  * engine   — one engine, behavior driven entirely by config.
  * registry — a stable interface + a registry of interchangeable plugins;
               config selects the implementation and passes its params.

This package defines *shape*, not behavior. A brand-new brick in any domain
conforms to the convention without changing brickkit.
"""
from __future__ import annotations

from .brick import BRICK_API, ENGINE, REGISTRY_KIND, BoundBrick, BrickModule
from .config import (
    BrickConfig,
    RegistryConfig,
    load_bundle,
    load_config,
    parse_envelope,
    validate_section,
)
from .pipeline import bind, run_pipeline, wire
from .registry import Registry, build_plugin
from .version import hash_dir, read_version

VERSION = "1.0.0"  # framework version (stamped, copied into every client)

__all__ = [
    "VERSION",
    "BRICK_API",
    "ENGINE",
    "REGISTRY_KIND",
    "BoundBrick",
    "BrickModule",
    "BrickConfig",
    "RegistryConfig",
    "load_config",
    "load_bundle",
    "validate_section",
    "parse_envelope",
    "Registry",
    "build_plugin",
    "run_pipeline",
    "bind",
    "wire",
    "hash_dir",
    "read_version",
]
