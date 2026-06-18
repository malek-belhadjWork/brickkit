"""folder source: list files in a directory matching one or more globs.

`glob` may be a single pattern ("*.pdf") or a list (["*.pdf", "*.png"]).
"""
from __future__ import annotations

from ..registry import REGISTRY


@REGISTRY.register("folder")
def make_folder(path: str, glob="*", recursive: bool = False):
    from pathlib import Path  # cheap; kept local to match the deferred-import rule

    patterns = [glob] if isinstance(glob, str) else list(glob)

    def fetch():
        base = Path(path)
        seen, out = set(), []
        for pat in patterns:
            it = base.rglob(pat) if recursive else base.glob(pat)
            for p in it:
                if p.is_file() and p not in seen:
                    seen.add(p)
                    out.append({"path": str(p), "name": p.name})
        out.sort(key=lambda r: r["name"])
        return out

    return fetch
