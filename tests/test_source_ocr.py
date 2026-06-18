"""Phase 2 proof: source fetches files; synthetic OCR reads a rendered crop."""
from __future__ import annotations

import sys
from pathlib import Path

from _harness import harness

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import textgen  # noqa: E402
from brickkit import load_config  # noqa: E402
from brickkit.bricks import ocr, source  # noqa: E402

test = harness(__name__)
TMP = ROOT / "tests" / "_tmp_phase2"


@test
def test_folder_source_lists_files():
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "a.png").write_bytes(b"x")
    (TMP / "b.png").write_bytes(b"x")
    (TMP / "ignore.txt").write_bytes(b"x")
    plugin = source.REGISTRY.create("folder", {"path": str(TMP), "glob": "*.png"})
    files = plugin()
    names = sorted(f["name"] for f in files)
    assert names == ["a.png", "b.png"], names


@test
def test_synthetic_ocr_reads_rendered_text():
    plugin = ocr.REGISTRY.create("synthetic", {"font_size": 26})
    for text in ["INV-000123", "1234.56", "2026-06-17"]:
        img = textgen.render_line(text, font_size=26)
        got, conf = plugin(img)
        assert got == text, f"{got!r} != {text!r} (conf={conf:.2f})"
        assert conf > 0.8, f"low confidence {conf:.2f} for {text!r}"


@test
def test_ocr_config_selects_plugin():
    cfg_path = TMP / "ocr.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        "brick: ocr\nimpl: synthetic\nparams: {font_size: 26}\n", encoding="utf-8"
    )
    cfg = load_config(ocr, cfg_path)
    assert cfg.impl == "synthetic"
    img = textgen.render_line("ACME", font_size=26)
    text, conf = ocr.run(img, cfg)
    assert text == "ACME", (text, conf)


@test
def test_registry_lists_all_plugins():
    assert set(ocr.REGISTRY.names()) == {"synthetic", "tesseract", "cloud"}
    assert set(source.REGISTRY.names()) == {"folder", "email", "s3"}


if __name__ == "__main__":
    test.main()
