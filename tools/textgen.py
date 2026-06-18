"""Fixture generator: render crisp text / synthetic invoices as PNGs.

A master-repo tool (not a brick, not copied into clients). Used by tests and to
produce sample invoices for the client proofs. Uses the same bundled font as the
synthetic OCR plugin so rendered text is recognizable offline. Real clients feed
real scans instead.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    return ImageFont.load_default(size=size)


def _draw_tracked(draw, x, y, text, font, gap):
    """Draw text one glyph at a time with a small fixed inter-letter gap, so the
    synthetic OCR can segment glyphs reliably. Word spaces are drawn distinctly
    wider than the inter-letter gap so they are unambiguous to the recognizer."""
    for ch in text:
        if ch == " ":
            x += int(round(font.getlength(" "))) + gap * 4
            continue
        draw.text((x, y), ch, fill=0, font=font)
        x += int(round(font.getlength(ch))) + gap
    return x


def _line_width(text, font, gap):
    total = 0
    for ch in text:
        if ch == " ":
            total += int(round(font.getlength(" "))) + gap * 4
        else:
            total += int(round(font.getlength(ch))) + gap
    return total - (gap if text else 0)


def render_line(text: str, font_size: int = 22, pad: int = 6, gap: int = 6) -> Image.Image:
    font = _font(font_size)
    asc, desc = font.getmetrics()
    w = _line_width(text, font, gap) + 2 * pad
    h = asc + desc + 2 * pad
    img = Image.new("L", (w, h), 255)
    _draw_tracked(ImageDraw.Draw(img), pad, pad, text, font, gap)
    return img


def render_invoice(
    fields: dict[str, str],
    layout: dict[str, tuple[float, float]],
    size: tuple[int, int] = (1000, 1400),
    font_size: int = 26,
    gap: int = 6,
) -> Image.Image:
    """Render a page-sized invoice. `layout` maps field name -> (x_ratio, y_ratio)
    of the text's top-left. Text content comes from `fields`."""
    font = _font(font_size)
    W, H = size
    img = Image.new("L", size, 255)
    draw = ImageDraw.Draw(img)
    for name, text in fields.items():
        if name not in layout:
            continue
        xr, yr = layout[name]
        _draw_tracked(draw, int(xr * W), int(yr * H), text, font, gap)
    return img


def save(img: Image.Image, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
