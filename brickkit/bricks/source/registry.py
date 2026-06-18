"""The source brick's own plugin registry."""
from __future__ import annotations

from brickkit.registry import Registry

# Stable interface: a built plugin is callable () -> list[dict].
# Each returned item is a file record: {"path": str, "name": str, ...}.
REGISTRY = Registry(interface="() -> list[{path, name}]")
