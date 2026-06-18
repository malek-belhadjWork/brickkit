"""Reconciliation — the mandatory rule of the extract brick.

Given the OCR readings collected across margins for one field:
  1. keep readings whose text matches the field's `format` regex (if any);
  2. among the kept readings, pick the HIGHEST confidence;
  3. cast the chosen text to the field's declared type.

If a format is configured but NO reading matches it, return the
highest-confidence raw reading with ``format_matched=False`` (best-effort value
+ a flag for downstream review) — never silently drop it.
"""
from __future__ import annotations

import re
from typing import Any


def cast_value(text: str, type_: str) -> Any:
    text = text.strip()
    if type_ == "string":
        return text
    if type_ == "int":
        digits = re.sub(r"[^0-9-]", "", text)
        try:
            return int(digits)
        except ValueError:
            return None
    if type_ == "money":
        s = re.sub(r"[^0-9.,-]", "", text)   # keep '-' so credits stay negative
        neg = s.startswith("-")
        s = s.lstrip("-")
        if "," in s and "." in s:
            s = s.replace(",", "")          # comma = thousands sep
        elif "," in s:
            s = s.replace(",", ".")         # comma = decimal sep
        try:
            value = round(float(s), 2)
        except ValueError:
            return None
        return -value if neg else value
    if type_ == "date":
        return text                          # already format-validated upstream
    return text


def reconcile(readings: list[tuple[str, float, int]], field) -> dict:
    """readings: list of (text, confidence, margin)."""
    fmt = field.format
    candidates = readings
    if fmt:
        good = [r for r in readings if re.fullmatch(fmt, r[0].strip())]
        if good:
            candidates, format_matched = good, True
        else:
            format_matched = False
    else:
        format_matched = True

    if not candidates:
        return {
            "value": None, "confidence": 0.0, "format_matched": False,
            "raw": "", "margin_used": None,
        }

    text, conf, margin = max(candidates, key=lambda r: r[1])
    return {
        "value": cast_value(text, field.type),
        "confidence": conf,
        "format_matched": format_matched,
        "raw": text.strip(),
        "margin_used": margin,
    }
