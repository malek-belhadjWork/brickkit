"""validate engine — required fields, confidence floor, cross-field checks.

Input: the list of extracted records from `extract`
  [{"source", "fields": {name: {value, confidence, format_matched, ...}}}].
Output: the same list, each record augmented with
  "validation": {"ok": bool, "flags": [{"field", "code", "detail"}]}.

`ok` is True when there are no flags. Flags are advisory and structured so a
downstream step (or a human) can route documents for review.
"""
from __future__ import annotations


def _flag(field, code, detail=""):
    return {"field": field, "code": code, "detail": detail}


def _check_record(fields: dict, config) -> list[dict]:
    flags = []

    for name in config.required:
        reading = fields.get(name)
        if reading is None or reading.get("value") in (None, ""):
            flags.append(_flag(name, "missing", "required field has no value"))

    for name, reading in fields.items():
        conf = reading.get("confidence", 0.0)
        if conf < config.min_confidence:
            flags.append(_flag(name, "low_confidence", f"{conf:.2f} < {config.min_confidence}"))
        if config.require_format and not reading.get("format_matched", True):
            flags.append(_flag(name, "format_mismatch", reading.get("raw", "")))

    for check in config.cross_checks:
        result = fields.get(check.result, {}).get("value")
        terms = [fields.get(t, {}).get("value") for t in check.terms]
        if result is None or any(t is None for t in terms):
            flags.append(_flag(check.result, "cross_check_incomputable",
                               f"need {check.result} and {check.terms}"))
            continue
        try:
            total = sum(float(t) for t in terms)
            if abs(float(result) - total) > check.tolerance:
                flags.append(_flag(
                    check.result, "cross_check",
                    f"{check.result}={result} != sum({check.terms})={total}",
                ))
        except (TypeError, ValueError):
            flags.append(_flag(check.result, "cross_check_incomputable", "non-numeric"))

    return flags


def run(data, config):
    out = []
    for rec in data:
        flags = _check_record(rec.get("fields", {}), config)
        rec = dict(rec)
        rec["validation"] = {"ok": not flags, "flags": flags}
        out.append(rec)
    return out
