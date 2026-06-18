"""email source (stub). Fill in as a self-contained plugin — adding it touches
nothing else. Heavy deps (imaplib config, attachment parsing) stay deferred."""
from __future__ import annotations

from ..registry import REGISTRY


@REGISTRY.register("email")
def make_email(**params):
    def fetch():
        raise NotImplementedError(
            "email source not implemented yet; add it as a plugin only"
        )

    return fetch
