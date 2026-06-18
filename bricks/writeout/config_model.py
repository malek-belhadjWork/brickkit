"""writeout config models."""
from __future__ import annotations

from brickkit.config import BrickConfig


class Config(BrickConfig):
    destination: str                       # output path (.csv)
    mapping: dict[str, str]                # field name -> output column header
    include_status: bool = True            # add ok/flags columns
    source_column: str | None = "source"   # column for the source file name
