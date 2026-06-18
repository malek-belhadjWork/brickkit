"""The core brick contract.

A brick is a Python package exposing module-level attributes:

    NAME: str            unique brick name; must match a config's ``brick:`` field
    VERSION: str         semver, stamped IN the brick (the canonical version)
    KIND: str            "engine" | "registry"
    CONFIG_MODEL: type   a pydantic model for the brick's config payload
    run(data, config)    the engine: engine(input, config) -> output

Registry bricks additionally expose ``REGISTRY`` (a ``brickkit.Registry``) and
select an implementation via ``config.impl``.

Engines are pure with respect to client state: every client/instance-specific
value lives in ``config``. No client name, path, or threshold is hardcoded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

BRICK_API = "1"  # framework contract version; bumped only on breaking shape changes

ENGINE = "engine"
REGISTRY_KIND = "registry"


@runtime_checkable
class BrickModule(Protocol):
    """Structural type a brick package satisfies. Used for documentation and
    light runtime checks — bricks are plain modules, not subclasses."""

    NAME: str
    VERSION: str
    KIND: str

    def run(self, data: Any, config: Any) -> Any: ...


@dataclass
class BoundBrick:
    """A brick module paired with its validated + resolved config.

    Running a BoundBrick preserves the ``engine(input, config)`` shape: the
    config (including any bound sub-bricks) is captured here once, so the
    pipeline only has to thread ``data`` from one stage to the next.
    """

    module: Any
    config: Any

    @property
    def name(self) -> str:
        return self.module.NAME

    @property
    def version(self) -> str:
        return self.module.VERSION

    @property
    def kind(self) -> str:
        return self.module.KIND

    def run(self, data: Any) -> Any:
        return self.module.run(data, self.config)
