"""cloud OCR plugin (stub). Demonstrates the registry's extensibility: adding a
real cloud engine is a new plugin only. SDK import stays deferred."""
from __future__ import annotations

from ..registry import REGISTRY


@REGISTRY.register("cloud")
def make_cloud(**params):
    def run(image, char_whitelist=None, **_):
        raise NotImplementedError(
            "cloud OCR not implemented yet; add it as a plugin only"
        )

    return run
