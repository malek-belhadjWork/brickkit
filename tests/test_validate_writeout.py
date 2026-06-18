"""Phase 4 proof: validate flags + writeout CSV (pure engine logic)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from _harness import harness

ROOT = Path(__file__).resolve().parent.parent

from brickkit.bricks import validate, writeout  # noqa: E402

test = harness(__name__)
TMP = ROOT / "tests" / "_tmp_phase4"


def _reading(value, conf=0.95, fmt=True, raw=None):
    return {"value": value, "confidence": conf, "format_matched": fmt,
            "raw": raw if raw is not None else str(value), "margin_used": 0}


def _records():
    good = {"source": "good.png", "fields": {
        "invoice_number": _reading("INV-000123"),
        "subtotal": _reading(1100.00), "tax": _reading(134.56),
        "total": _reading(1234.56)}}
    bad = {"source": "bad.png", "fields": {
        "invoice_number": _reading("INV-000999", conf=0.30),   # low confidence
        "subtotal": _reading(1000.00), "tax": _reading(100.00),
        "total": _reading(1234.56),                            # 1000+100 != 1234.56
        "date": _reading("xx", fmt=False)}}                    # format mismatch
    return [good, bad]


def _validate_cfg():
    return validate.CONFIG_MODEL.model_validate({
        "required": ["invoice_number", "total"],
        "min_confidence": 0.5,
        "cross_checks": [{"kind": "sum", "result": "total",
                          "terms": ["subtotal", "tax"], "tolerance": 0.01}],
    })


@test
def test_validate_flags_and_ok():
    out = validate.run(_records(), _validate_cfg())
    good, bad = out
    assert good["validation"]["ok"] is True, good["validation"]
    codes = {f["code"] for f in bad["validation"]["flags"]}
    assert "low_confidence" in codes
    assert "cross_check" in codes
    assert "format_mismatch" in codes
    assert bad["validation"]["ok"] is False


@test
def test_writeout_csv_mapping():
    TMP.mkdir(parents=True, exist_ok=True)
    dest = TMP / "out.csv"
    validated = validate.run(_records(), _validate_cfg())
    cfg = writeout.CONFIG_MODEL.model_validate({
        "destination": str(dest),
        "mapping": {"invoice_number": "Invoice #", "total": "Amount"},
    })
    summary = writeout.run(validated, cfg)
    assert summary["written"] == 2
    rows = list(csv.DictReader(dest.open(encoding="utf-8")))
    assert rows[0]["Invoice #"] == "INV-000123"
    assert rows[0]["Amount"] == "1234.56"
    assert rows[0]["valid"] == "True"
    assert rows[1]["valid"] == "False"
    assert "source" in rows[0]


if __name__ == "__main__":
    test.main()
