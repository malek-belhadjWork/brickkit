from __future__ import annotations

from .. import REGISTRY


@REGISTRY.register("lower")
def make_lower():
    return lambda text: text.lower()
