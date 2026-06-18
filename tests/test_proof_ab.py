"""Phase 5+6 — THE PROOF.

Build the document bricks once, then make two clients with DIFFERENT templates
work by editing ONLY config. The acceptance check: the engine files copied into
client_A and client_B are byte-identical — every difference lives in config.
"""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

from _harness import harness

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import brickctl  # noqa: E402
import textgen  # noqa: E402

test = harness(__name__)

# Build the proof's throwaway clients in an isolated dir so this test never
# touches the real clients/client_A and clients/client_B (which carry real PDFs).
PROOF_DIR = ROOT / "tests" / "_proof_clients"

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-./:#,$ "

# --- two different invoice templates --------------------------------------
TEMPLATE_A = {
    "size": (1500, 2100),
    "values": {"invoice_number": "INV-000123", "date": "2026-06-18",
               "subtotal": "1100.00", "tax": "134.56", "total": "1234.56"},
    "layout": {"invoice_number": (0.08, 0.10), "date": (0.08, 0.16),
               "subtotal": (0.62, 0.66), "tax": (0.62, 0.72), "total": (0.62, 0.78)},
}
TEMPLATE_B = {
    "size": (1700, 2340),
    "values": {"ref": "B2026/0042", "inv_date": "18.06.2026",
               "net": "900.00", "vat": "180.00", "gross": "1080.00"},
    "layout": {"ref": (0.55, 0.08), "inv_date": (0.55, 0.13),
               "net": (0.10, 0.80), "vat": (0.38, 0.80), "gross": (0.66, 0.80)},
}


def _box(x, y, w=0.26, h=0.04):
    return [round(x - 0.01, 4), round(y - 0.01, 4), w, h]


# --- per-client config: ONE config.yaml, the only thing that differs ------
def _fields_yaml(fields):
    lines = ["  fields:"]
    for name, type_, box, fmt in fields:
        lines.append(
            f"    - {{name: {name}, type: {type_}, box: {box}, "
            f"margins: [2, 6, 10], format: '{fmt}'}}"
        )
    return "\n".join(lines)


def _config_A():
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
source: {{impl: folder, params: {{path: ./data/in, glob: '*.png'}}}}
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
  destination: ./data/out/clientA.csv
  mapping: {{invoice_number: 'Invoice #', date: 'Date', total: 'Amount'}}
"""


def _config_B():
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
source: {{impl: folder, params: {{path: ./data/in, glob: '*.png'}}}}
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
  destination: ./data/out/clientB.csv
  mapping: {{ref: 'Reference', inv_date: 'Invoice Date', gross: 'Grand Total'}}
"""


# --- build + run a client -------------------------------------------------
def _make_client(name, template, config_yaml):
    client = PROOF_DIR / name
    if client.exists():
        brickctl._make_writable(client)
        shutil.rmtree(client)
    brickctl.cmd_scaffold(type("A", (), {"client": str(client)}))
    brickctl.cmd_sync(type("A", (), {"client": str(client), "brick": None}))

    # the ONLY client-specific surface: a single config.yaml
    (client / "config.yaml").write_text(config_yaml, encoding="utf-8")

    # generate sample invoices for this template
    img = textgen.render_invoice(
        template["values"], template["layout"],
        size=template["size"], font_size=int(0.028 * template["size"][0]),
    )
    textgen.save(img, client / "data" / "in" / "sample01.png")
    return client


def _run_client(client):
    result = subprocess.run(
        [sys.executable, "main.py"], cwd=client,
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out_csv = next((client / "data" / "out").glob("*.csv"))
    return list(csv.DictReader(out_csv.open(encoding="utf-8")))


@test
def test_client_A_then_B_by_config_only():
    try:
        a = _make_client("client_A", TEMPLATE_A, _config_A())
        b = _make_client("client_B", TEMPLATE_B, _config_B())

        rows_a = _run_client(a)
        assert rows_a[0]["Invoice #"] == "INV-000123", rows_a
        assert float(rows_a[0]["Amount"]) == 1234.56
        assert rows_a[0]["valid"] == "True", rows_a  # cross-check + confidence pass

        rows_b = _run_client(b)
        assert rows_b[0]["Reference"] == "B2026/0042", rows_b
        assert float(rows_b[0]["Grand Total"]) == 1080.00
        assert rows_b[0]["valid"] == "True", rows_b

        # THE ACCEPTANCE CHECK: engines are byte-identical across clients.
        ha = brickctl.hash_dir(a / "engines")
        hb = brickctl.hash_dir(b / "engines")
        assert ha == hb, "engine files differ between clients — design leak!"
        assert brickctl.cmd_verify(type("A", (), {"client": str(a)})) == 0
        assert brickctl.cmd_verify(type("A", (), {"client": str(b)})) == 0
    finally:
        if PROOF_DIR.exists():
            brickctl._make_writable(PROOF_DIR)
            shutil.rmtree(PROOF_DIR)


if __name__ == "__main__":
    test.main()
