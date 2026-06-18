"""Verify a REAL OCR engine (Tesseract) end-to-end.

Run this after installing Tesseract:

    python tools/check_ocr.py
    python tools/check_ocr.py "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

It generates a sample invoice, runs the document pipeline with `impl: tesseract`,
and prints the per-field OCR and the resulting CSV row. The only difference from
the offline `synthetic` run is one config value: impl.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bricks"))
sys.path.insert(0, str(ROOT / "tools"))

import textgen  # noqa: E402
from brickkit import run_pipeline, validate_section, wire  # noqa: E402

CMD = sys.argv[1] if len(sys.argv) > 1 else None

VALUES = {"invoice_number": "INV-000123", "date": "2026-06-18",
          "subtotal": "1100.00", "tax": "134.56", "total": "1234.56"}
LAYOUT = {"invoice_number": (0.08, 0.10), "date": (0.08, 0.16),
          "subtotal": (0.62, 0.66), "tax": (0.62, 0.72), "total": (0.62, 0.78)}


def _box(x, y, w=0.26, h=0.04):
    return [round(x - 0.01, 4), round(y - 0.01, 4), w, h]


def _preflight():
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        sys.exit("pytesseract missing — run: python -m pip install pytesseract")
    import ocr  # noqa: E402
    try:
        plug = ocr.REGISTRY.create("tesseract", {"cmd": CMD} if CMD else {})
        from PIL import Image
        plug(Image.new("L", (60, 30), 255))  # trivial call; raises if binary absent
    except Exception as e:  # pytesseract.TesseractNotFoundError and friends
        sys.exit(
            "Tesseract engine not found.\n"
            f"  ({type(e).__name__}: {e})\n\n"
            "Install it (free): https://github.com/UB-Mannheim/tesseract/wiki\n"
            "Default path: C:\\Program Files\\Tesseract-OCR\\tesseract.exe\n"
            "Then either add it to PATH, or pass the path:\n"
            '  python tools/check_ocr.py "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"'
        )


def main():
    _preflight()
    import extract
    import ocr
    import source
    import validate
    import writeout

    demo = ROOT / "tools" / "_ocr_demo"
    indir, outdir = demo / "in", demo / "out"
    indir.mkdir(parents=True, exist_ok=True)
    textgen.save(textgen.render_invoice(VALUES, LAYOUT, size=(1500, 2100),
                                        font_size=42), indir / "sample01.png")

    ocr_params = {"psm": 7}
    if CMD:
        ocr_params["cmd"] = CMD
    bundle = {
        "source": {"impl": "folder", "params": {"path": str(indir), "glob": "*.png"}},
        "ocr": {"impl": "tesseract", "params": ocr_params},
        "extract": {"canonical": {"long_side_px": 1500}, "fields": [
            {"name": "invoice_number", "type": "string", "box": _box(*LAYOUT["invoice_number"]), "margins": [4, 8], "format": r"INV-\d{6}"},
            {"name": "date", "type": "date", "box": _box(*LAYOUT["date"]), "margins": [4, 8], "format": r"\d{4}-\d{2}-\d{2}"},
            {"name": "subtotal", "type": "money", "box": _box(*LAYOUT["subtotal"], 0.24), "margins": [4, 8], "format": r"\d+\.\d{2}"},
            {"name": "tax", "type": "money", "box": _box(*LAYOUT["tax"], 0.24), "margins": [4, 8], "format": r"\d+\.\d{2}"},
            {"name": "total", "type": "money", "box": _box(*LAYOUT["total"], 0.24), "margins": [4, 8], "format": r"\d+\.\d{2}"},
        ]},
        "validate": {"required": ["invoice_number", "total"], "min_confidence": 0.4,
                     "cross_checks": [{"result": "total", "terms": ["subtotal", "tax"], "tolerance": 0.02}]},
        "writeout": {"destination": str(outdir / "out.csv"),
                     "mapping": {"invoice_number": "Invoice #", "date": "Date", "total": "Amount"}},
    }
    modules = {"source": source, "ocr": ocr, "extract": extract,
               "validate": validate, "writeout": writeout}
    configs = {n: validate_section(modules[n], bundle[n]) for n in modules}
    bound = wire(modules, configs)

    files = bound["source"].run(None)
    records = bound["extract"].run(files)
    print("\nPer-field OCR (engine: tesseract):")
    for name, r in records[0]["fields"].items():
        ok = "ok" if r["format_matched"] else "??"
        print(f"  [{ok}] {name:15} = {str(r['value']):14} conf={r['confidence']:.2f} raw={r['raw']!r}")

    records = bound["validate"].run(records)
    summary = bound["writeout"].run(records)
    print(f"\nvalidation ok: {records[0]['validation']['ok']}")
    print(f"wrote: {summary}")
    print("\nCSV:")
    print((outdir / "out.csv").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
