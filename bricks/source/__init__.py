"""source — registry brick. Fetch input files. `fetch() -> [file records]`.

KIND=registry. Plugins: folder (implemented), email/s3 (stubs to be filled in
as new plugins only). Config selects one via `impl`.
"""
from __future__ import annotations

from .config_model import Config
from .registry import REGISTRY

NAME = "source"
VERSION = "1.0.0"
KIND = "registry"
CONFIG_MODEL = Config

# Explicit plugin imports register the implementations.
from . import plugins  # noqa: E402,F401


def run(data, config):
    """data is ignored — source is the first stage. Returns a list of file
    records for the next brick to process."""
    plugin = REGISTRY.create(config.impl, config.params)
    return plugin()
