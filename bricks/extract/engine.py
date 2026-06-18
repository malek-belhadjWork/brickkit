"""extract engine — zonal/template OCR with mandatory reconciliation.

For each input file: load (grayscale, NOT resampled), then for each configured
field: locate the region, crop it at each configured margin, call the injected
OCR brick per crop, and reconcile the readings.

Resolution independence: field boxes are RATIOS (0..1) of page size, so they
locate the same region at any DPI. The page is NOT resampled (resampling
discards detail OCR needs); instead the `canonical` long side is just the
reference unit for margins, which are scaled to native pixels per image
(margin_native = margin * native_long_side / canonical_long_side). Same config,
any scan resolution.
"""
from __future__ import annotations

from .locators import locate
from .reconcile import reconcile


def _load_image(path, dpi: int, page: int):
    """Load an input as a grayscale PIL image. PDFs are rasterized at `dpi`
    (PyMuPDF import deferred so it's only required when PDFs are used)."""
    from PIL import Image

    if str(path).lower().endswith(".pdf"):
        import fitz  # PyMuPDF — deferred; only needed for PDF inputs

        doc = fitz.open(path)
        pix = doc[page].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
        return Image.frombytes("L", (pix.width, pix.height), pix.samples)
    return Image.open(path).convert("L")


def _crop(img, box_px, margin: int):
    x, y, w, h = box_px
    W, H = img.size
    left = max(0, int(round(x - margin)))
    top = max(0, int(round(y - margin)))
    right = min(W, int(round(x + w + margin)))
    bottom = min(H, int(round(y + h + margin)))
    return img.crop((left, top, right, bottom))


def run(data, config):
    """data: list of file records [{"path", "name"}]. Returns a list of
    extracted records: [{"source", "fields": {name: reading}}]."""
    if config.ocr is None:
        raise RuntimeError(
            "extract requires an OCR sub-brick; wire INJECTS={'ocr': 'ocr'} "
            "(brickkit.pipeline.wire) before running"
        )

    results = []
    for rec in data:
        # Pages are loaded on demand and cached (a field may target a specific
        # PDF page; multi-page invoices put header and totals on different pages).
        page_cache: dict[int, object] = {}

        def page_image(page_index: int):
            if page_index not in page_cache:
                page_cache[page_index] = _load_image(
                    rec["path"], config.pdf_dpi, page_index
                )
            return page_cache[page_index]

        fields = {}
        for field in config.fields:
            page_index = field.page if field.page is not None else config.pdf_page
            img = page_image(page_index)
            size = img.size
            # margins are in canonical pixels; scale to this image's pixels
            scale = max(size) / config.canonical.long_side_px
            box_px = locate(field.locator, size)
            readings = []
            for margin in field.margins:
                m_native = int(round(margin * scale))
                text, conf = config.ocr(
                    _crop(img, box_px, m_native), char_whitelist=field.chars
                )
                readings.append((text, conf, margin))
            fields[field.name] = reconcile(readings, field)
        results.append({"source": rec["name"], "fields": fields})
    return results
