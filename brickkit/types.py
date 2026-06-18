"""Framework-generic typing aliases and the inter-brick data convention.

Data passed *between* bricks in a pipeline is plain JSON-able Python (dicts,
lists, scalars) — NOT a shared class. This keeps bricks independent units that
can be copied individually without dragging in a shared-types module: a brick
only needs to agree on the *shape* of the dict it receives and emits, documented
in its own engine. (Bricks may use dataclasses internally; the boundary stays
dict-shaped.)
"""
from __future__ import annotations

from typing import Any, Union

JSONScalar = Union[str, int, float, bool, None]
JSON = Union[JSONScalar, dict[str, "JSON"], list["JSON"]]
Record = dict[str, Any]
