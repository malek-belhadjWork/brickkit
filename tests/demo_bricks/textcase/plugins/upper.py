from __future__ import annotations

from .. import REGISTRY


@REGISTRY.register("upper")
def make_upper():
    # A real plugin would defer heavy third-party imports to here.
    return lambda text: text.upper()
