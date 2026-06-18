"""Stable interface for the `source` registry brick.

A source plugin fetches input files from somewhere (folder, email, S3, ...).

    fetch() -> list[FileRecord]

where FileRecord is a plain dict::

    {"path": str, "name": str}   # additional keys allowed (e.g. received_at)

New sources are added as new plugins only; this signature never changes, so no
downstream brick (extract, validate, writeout) is affected.
"""
from __future__ import annotations

from typing import Any, Protocol


class FetchPlugin(Protocol):
    def __call__(self) -> list[dict[str, Any]]: ...
