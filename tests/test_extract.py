"""Phase 3 proof: zonal extract + reconciliation + resolution independence."""
from __future__ import annotations

import sys
from pathlib import Path

from _harness import harness

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bricks"))
sys.path.insert(0, str(ROOT / "tools"))

import extract  # noqa: E402
import ocr  # noqa: E402
import textgen  # noqa: E402
from brickkit import wire  # noqa: E402

test = harness(__name__)
TMP = ROOT / "tests" / "_tmp_phase3"

LAYOUT = {"invoice_number": (0.10, 0.08), "date": (0.10, 0.14), "total": (0.62, 0.82)}
VALUES = {"invoice_number": "INV-000123", "date": "2026-06-18", "total": "1234.56"}

# Invoice field values use a restricted charset (no lowercase) — a legitimate
# per-client OCR tuning that removes confusable templates.
INVOICE_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-./:#,$"
CANONICAL = 1500  # reference unit for margins (image is NOT resampled)


def _boxes():
    return {n: (x - 0.01, y - 0.01, 0.26, 0.035) for n, (x, y) in LAYOUT.items()}


def _extract_config(extra_fields=None):
    boxes = _boxes()
    fields = [
        {"name": "invoice_number", "type": "string",
         "locator": {"kind": "fixed", "box": list(boxes["invoice_number"])},
         "margins": [2, 5, 8], "format": r"INV-\d{6}"},
        {"name": "date", "type": "date",
         "locator": {"kind": "fixed", "box": list(boxes["date"])},
         "margins": [2, 5, 8], "format": r"\d{4}-\d{2}-\d{2}"},
        {"name": "total", "type": "money",
         "locator": {"kind": "fixed", "box": list(boxes["total"])},
         "margins": [2, 5, 8], "format": r"\d+\.\d{2}"},
    ]
    if extra_fields:
        fields += extra_fields
    return extract.CONFIG_MODEL.model_validate(
        {"canonical": {"long_side_px": CANONICAL}, "fields": fields}
    )


def _wire(extract_cfg):
    ocr_cfg = ocr.CONFIG_MODEL.model_validate(
        {"impl": "synthetic",
         "params": {"font_size": 44, "charset": INVOICE_CHARSET}}
    )
    bound = wire({"extract": extract, "ocr": ocr},
                 {"extract": extract_cfg, "ocr": ocr_cfg})
    return bound["extract"]


def _render(path, size):
    img = textgen.render_invoice(VALUES, LAYOUT, size=size,
                                 font_size=int(0.029 * size[0]))
    return textgen.save(img, path)


@test
def test_extract_reads_fields_and_reconciles():
    TMP.mkdir(parents=True, exist_ok=True)
    _render(TMP / "a.png", (1500, 2100))
    bound = _wire(_extract_config())
    [out] = bound.run([{"path": str(TMP / "a.png"), "name": "a.png"}])
    f = out["fields"]
    assert f["invoice_number"]["value"] == "INV-000123", f["invoice_number"]
    assert f["invoice_number"]["format_matched"] is True
    assert f["date"]["value"] == "2026-06-18", f["date"]
    assert f["total"]["value"] == 1234.56, f["total"]
    assert f["total"]["confidence"] > 0.8


@test
def test_resolution_independence():
    TMP.mkdir(parents=True, exist_ok=True)
    _render(TMP / "lo.png", (1500, 2100))
    _render(TMP / "hi.png", (2250, 3150))  # 1.5x DPI
    bound = _wire(_extract_config())
    lo = bound.run([{"path": str(TMP / "lo.png"), "name": "lo"}])[0]["fields"]
    hi = bound.run([{"path": str(TMP / "hi.png"), "name": "hi"}])[0]["fields"]
    for name in VALUES:
        assert lo[name]["value"] == hi[name]["value"], (name, lo[name], hi[name])


@test
def test_no_format_match_keeps_best_effort_and_flags():
    TMP.mkdir(parents=True, exist_ok=True)
    _render(TMP / "a.png", (1500, 2100))
    # invoice_number value is "INV-000123" but we demand an impossible format
    cfg = _extract_config()
    cfg.fields[0].format = r"ZZZ\d{3}"
    bound = _wire(cfg)
    out = bound.run([{"path": str(TMP / "a.png"), "name": "a.png"}])[0]
    inv = out["fields"]["invoice_number"]
    assert inv["format_matched"] is False
    assert inv["raw"] == "INV-000123"   # best-effort value retained for review


if __name__ == "__main__":
    test.main()
