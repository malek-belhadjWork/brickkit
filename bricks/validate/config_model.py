"""validate config models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from brickkit.config import BrickConfig


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrossCheck(_Strict):
    kind: Literal["sum"] = "sum"   # result == sum(terms) within tolerance
    result: str
    terms: list[str]
    tolerance: float = 0.0


class Config(BrickConfig):
    required: list[str] = []           # fields that must have a value
    min_confidence: float = 0.0        # per-field confidence floor
    require_format: bool = True        # flag fields whose format didn't match
    cross_checks: list[CrossCheck] = []
