"""Versioning + drift-detection helpers.

Each brick stamps its own ``VERSION`` constant (the canonical version). When a
brick is copied into a client, its files are hashed and recorded in the client
manifest so ``brickctl verify`` can prove the copy was never edited in place.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def read_version(brick_module: Any) -> str:
    return brick_module.VERSION


def hash_dir(path: str | Path) -> dict[str, str]:
    """Map of relative ``*.py`` path -> sha256 for every file under ``path``.

    Used to stamp a copied engine into the manifest and later detect drift.
    """
    path = Path(path)
    out: dict[str, str] = {}
    for p in sorted(path.rglob("*.py")):
        rel = p.relative_to(path).as_posix()
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def diff_hashes(
    expected: dict[str, str], actual: dict[str, str]
) -> dict[str, list[str]]:
    """Compare two hash maps. Returns {"modified": [...], "added": [...],
    "removed": [...]} — all empty means the copy is pristine."""
    exp, act = set(expected), set(actual)
    return {
        "modified": sorted(k for k in exp & act if expected[k] != actual[k]),
        "added": sorted(act - exp),
        "removed": sorted(exp - act),
    }
