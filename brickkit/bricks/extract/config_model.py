"""extract config models.

Field boxes are RATIOS (0..1) of page width/height — resolution-independent.
The engine also normalizes every input to a canonical resolution so margins (in
canonical pixels) have a stable unit.

The `locator` is a strategy seam: v1 ships `fixed` (a ratio box). A future
`anchor` locator (find a label, offset from it) is added as a new locator kind —
the reconciliation logic and config schema around it stay the same, so switching
a client to anchors becomes a config-only change once anchor ships.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brickkit.config import BrickConfig


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Canonical(_Strict):
    long_side_px: int = 2000


class FixedLocator(_Strict):
    kind: Literal["fixed"] = "fixed"
    box: tuple[float, float, float, float]  # x, y, w, h as ratios 0..1


# v1 union has a single member; adding AnchorLocator later extends this union.
Locator = FixedLocator


class FieldConfig(_Strict):
    name: str
    type: Literal["string", "int", "money", "date"] = "string"
    locator: FixedLocator | None = None
    margins: list[int] = [0]      # canonical px tried around the box
    format: str | None = None     # regex; reconciliation keeps format-matching reads
    page: int | None = None       # PDF page for this field (default: config.pdf_page)
    chars: str | None = None      # restrict OCR to these characters for this field
                                  # (e.g. "CN0123456789" so a 0 can't be read as O)

    @model_validator(mode="before")
    @classmethod
    def _box_shorthand(cls, data):
        # Allow `box: [x,y,w,h]` as shorthand for `locator: {kind: fixed, box: ...}`.
        if isinstance(data, dict) and "box" in data and "locator" not in data:
            data = dict(data)
            data["locator"] = {"kind": "fixed", "box": data.pop("box")}
        return data

    @model_validator(mode="after")
    def _require_locator(self):
        if self.locator is None:
            raise ValueError(f"field {self.name!r} needs a 'box' or 'locator'")
        return self


class Config(BrickConfig):
    canonical: Canonical = Canonical()
    pdf_dpi: int = 200          # rasterization DPI for PDF inputs
    pdf_page: int = 0           # which PDF page to read (0-based)
    fields: list[FieldConfig]
    # Injected at wiring time by INJECTS={"ocr": "ocr"}; never present in YAML.
    ocr: Any = Field(default=None, exclude=True)
