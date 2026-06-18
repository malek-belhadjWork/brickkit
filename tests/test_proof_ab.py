"""THE PROOF (packaged model).

Two clients with DIFFERENT templates work by editing ONLY config — same installed
`brickkit`, nothing copied per client. Acceptance: no per-client engine files
exist (it's all the one package) and the only difference is each config.yaml.
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

from _harness import harness

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import textgen  # noqa: E402
from brickkit import discover_bricks, run_config  # noqa: E402

test = harness(__name__)
PROOF_DIR = ROOT / "tests" / "_proof_clients"
CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-./:#,$ "

# --- two different invoice templates --------------------------------------
TEMPLATE_A = {
    "size": (1500, 2100), "canonical": 1500,
    "values": {"invoice_number": "INV-000123", "date": "2026-06-18",
               "subtotal": "1100.00", "tax": "134.56", "total": "1234.56"},
    "layout": {"invoice_number": (0.08, 0.10), "date": (0.08, 0.16),
               "subtotal": (0.62, 0.66), "tax": (0.62, 0.72), "total": (0.62, 0.78)},
}
TEMPLATE_B = {
    "size": (1700, 2340), "canonical": 1700,
    "values": {"ref": "B2026/0042", "inv_date": "18.06.2026",
               "net": "900.00", "vat": "180.00", "gross": "1080.00"},
    "layout": {"ref": (0.55, 0.08), "inv_date": (0.55, 0.13),
               "net": (0.10, 0.80), "vat": (0.38, 0.80), "gross": (0.66, 0.80)},
}


def _box(x, y, w=0.26, h=0.04):
    return [round(x - 0.01, 4), round(y - 0.01, 4), w, h]


def _fields_yaml(fields):
    lines = ["  fields:"]
    for name, type_, box, fmt in fields:
        lines.append(
            f"    - {{name: {name}, type: {type_}, box: {box}, "
            f"margins: [2, 6, 10], format: '{fmt}'}}"
        )
    return "\n".join(lines)


def _config_A(indir, outcsv):
    L = TEMPLATE_A["layout"]
    fields = _fields_yaml([
        ("invoice_number", "string", _box(*L["invoice_number"]), r"INV-\d{6}"),
        ("date", "date", _box(*L["date"]), r"\d{4}-\d{2}-\d{2}"),
        ("subtotal", "money", _box(*L["subtotal"], 0.24), r"\d+\.\d{2}"),
        ("tax", "money", _box(*L["tax"], 0.24), r"\d+\.\d{2}"),
        ("total", "money", _box(*L["total"], 0.24), r"\d+\.\d{2}"),
    ])
    return f"""\
pipeline: [source, extract, validate, writeout]
source: {{impl: folder, params: {{path: '{indir}', glob: '*.png'}}}}
ocr: {{impl: synthetic, params: {{font_size: 44, charset: "{CHARSET}"}}}}
extract:
  canonical: {{long_side_px: 1500}}
{fields}
validate:
  required: [invoice_number, total]
  min_confidence: 0.5
  cross_checks:
    - {{result: total, terms: [subtotal, tax], tolerance: 0.02}}
writeout:
  destination: '{outcsv}'
  mapping: {{invoice_number: 'Invoice #', date: 'Date', total: 'Amount'}}
"""


def _config_B(indir, outcsv):
    L = TEMPLATE_B["layout"]
    fields = _fields_yaml([
        ("ref", "string", _box(*L["ref"], 0.30), r"[A-Z]\d{4}/\d{4}"),
        ("inv_date", "date", _box(*L["inv_date"], 0.30), r"\d{2}\.\d{2}\.\d{4}"),
        ("net", "money", _box(*L["net"], 0.18), r"\d+\.\d{2}"),
        ("vat", "money", _box(*L["vat"], 0.18), r"\d+\.\d{2}"),
        ("gross", "money", _box(*L["gross"], 0.18), r"\d+\.\d{2}"),
    ])
    return f"""\
pipeline: [source, extract, validate, writeout]
source: {{impl: folder, params: {{path: '{indir}', glob: '*.png'}}}}
ocr: {{impl: synthetic, params: {{font_size: 44, charset: "{CHARSET}"}}}}
extract:
  canonical: {{long_side_px: 1700}}
{fields}
validate:
  required: [ref, gross]
  min_confidence: 0.5
  cross_checks:
    - {{result: gross, terms: [net, vat], tolerance: 0.02}}
writeout:
  destination: '{outcsv}'
  mapping: {{ref: 'Reference', inv_date: 'Invoice Date', gross: 'Grand Total'}}
"""


def _make_client(name, template, config_fn):
    client = PROOF_DIR / name
    indir, outdir = client / "data" / "in", client / "data" / "out"
    indir.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    outcsv = outdir / f"{name}.csv"
    (client / "config.yaml").write_text(
        config_fn(indir.as_posix(), outcsv.as_posix()), encoding="utf-8"
    )
    img = textgen.render_invoice(
        template["values"], template["layout"],
        size=template["size"], font_size=int(0.028 * template["size"][0]),
    )
    textgen.save(img, indir / "sample01.png")
    return client, outcsv


def _rows(csv_path):
    return list(csv.DictReader(csv_path.open(encoding="utf-8")))


@test
def test_two_templates_by_config_only():
    try:
        a, a_csv = _make_client("client_A", TEMPLATE_A, _config_A)
        b, b_csv = _make_client("client_B", TEMPLATE_B, _config_B)

        run_config(a / "config.yaml")
        run_config(b / "config.yaml")

        rows_a, rows_b = _rows(a_csv), _rows(b_csv)
        assert rows_a[0]["Invoice #"] == "INV-000123", rows_a
        assert float(rows_a[0]["Amount"]) == 1234.56
        assert rows_a[0]["valid"] == "True", rows_a

        assert rows_b[0]["Reference"] == "B2026/0042", rows_b
        assert float(rows_b[0]["Grand Total"]) == 1080.00
        assert rows_b[0]["valid"] == "True", rows_b

        # ACCEPTANCE: nothing is copied per client — no engines/, just config.yaml,
        # and both run on the same installed package's discovered bricks.
        assert not (a / "engines").exists() and not (b / "engines").exists()
        assert {"source", "ocr", "extract", "validate", "writeout"} <= set(
            discover_bricks()
        )
    finally:
        shutil.rmtree(PROOF_DIR, ignore_errors=True)


if __name__ == "__main__":
    test.main()
