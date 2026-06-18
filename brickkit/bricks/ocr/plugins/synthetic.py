"""synthetic OCR plugin — a small but real template-matching recognizer.

Dependency-free (Pillow only). It builds glyph templates from a known font/size,
segments an image crop into glyphs by ink-column projection, normalizes each
glyph to a fixed grid, and matches it against the templates using cosine
similarity on ink-weighted intensities (so the white background doesn't make
every sparse glyph look alike). Confidence is the mean per-glyph cosine (0..1).

This makes the document pipeline runnable end-to-end with no external OCR engine
installed. It is just one plugin behind the stable ocr interface — production
clients select `tesseract` (or another engine) by config instead.
"""
from __future__ import annotations

from ..registry import REGISTRY

DEFAULT_CHARSET = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "-./:#,$"
)


@REGISTRY.register("synthetic")
def make_synthetic(
    font_size: int = 40,
    threshold: int = 128,
    charset: str = DEFAULT_CHARSET,
    tpl_w: int = 32,
    tpl_h: int = 46,
    space_frac: float = 0.45,
):
    return _Synthetic(font_size, threshold, charset, tpl_w, tpl_h, space_frac)


class _Synthetic:
    def __init__(self, font_size, threshold, charset, tpl_w, tpl_h, space_frac):
        from PIL import ImageFont

        self.threshold = threshold
        self.tpl = (tpl_w, tpl_h)
        self.space_frac = space_frac
        self.font_size = font_size
        self.font = ImageFont.load_default(size=font_size)
        # template char -> binary ink grid
        self.templates = {}
        for ch in charset:
            vec = self._render_template(ch)
            if vec is not None:
                self.templates[ch] = vec

    # --- template construction --------------------------------------------
    def _render_template(self, ch):
        from PIL import Image, ImageChops, ImageDraw

        pad = self.font_size
        img = Image.new("L", (self.font_size * 3, self.font_size * 3), 255)
        ImageDraw.Draw(img).text((pad, pad), ch, fill=0, font=self.font)
        bbox = ImageChops.invert(img).getbbox()
        if bbox is None:  # e.g. space rendered nothing
            return None
        return self._normalize(img.crop(bbox))

    def _normalize(self, gray):
        """Fit a glyph into the template grid PRESERVING aspect ratio (centered),
        and return a flat tuple of INK intensities (255 = full ink, 0 = blank).

        Aspect preservation keeps a thin 'I' from colliding with '-'; ink
        weighting + cosine matching keeps sparse glyphs (-, :, .) apart."""
        from PIL import Image

        w, h = self.tpl
        gw, gh = gray.size
        scale = min(w / gw, h / gh)
        nw, nh = max(1, round(gw * scale)), max(1, round(gh * scale))
        resized = gray.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("L", (w, h), 255)
        canvas.paste(resized, ((w - nw) // 2, (h - nh) // 2))
        px = canvas.load()
        # Binarize: ink=1, else 0. Binarizing AFTER the grid-fit removes the
        # anti-aliasing blur that resampling (page normalization) introduces, so
        # a crisp template still matches a downscaled glyph. Cosine over these
        # ink vectors keeps the background out of the score.
        return tuple(
            1 if px[x, y] < self.threshold else 0
            for y in range(h)
            for x in range(w)
        )

    # --- recognition ------------------------------------------------------
    def __call__(self, image, char_whitelist=None, **_):
        gray = image.convert("L")
        w, h = gray.size
        if w == 0 or h == 0:
            return "", 0.0
        px = gray.load()
        col_has_ink = [
            any(px[x, y] < self.threshold for y in range(h)) for x in range(w)
        ]

        spans = []
        x = 0
        while x < w:
            if col_has_ink[x]:
                start = x
                while x < w and col_has_ink[x]:
                    x += 1
                spans.append((start, x))
            else:
                x += 1
        if not spans:
            return "", 0.0

        widths = [b - a for a, b in spans]
        median_w = sorted(widths)[len(widths) // 2]
        gaps = [spans[i][0] - spans[i - 1][1] for i in range(1, len(spans))]
        # A real word-space is much wider than the natural inter-letter gap of a
        # proportional font; classify adaptively (vs the median gap) with a floor
        # tied to glyph width, so single-token fields never split spuriously.
        median_gap = sorted(gaps)[len(gaps) // 2] if gaps else 0
        space_gap = max(median_gap * 2.2, median_w * 0.9)

        chars, scores = [], []
        prev_end = None
        for a, b in spans:
            if prev_end is not None and (a - prev_end) > space_gap:
                chars.append(" ")
            ch, score = self._match(gray.crop((a, 0, b, h)))
            if ch is not None:
                chars.append(ch)
                scores.append(score)
            prev_end = b

        text = "".join(chars).strip()
        confidence = sum(scores) / len(scores) if scores else 0.0
        return text, confidence

    def _match(self, glyph_gray):
        from PIL import ImageChops

        bbox = ImageChops.invert(glyph_gray).getbbox()
        if bbox is None:
            return None, 0.0
        vec = self._normalize(glyph_gray.crop(bbox))
        n = len(vec)
        best_ch, best_score = None, -1.0
        for ch, tpl in self.templates.items():
            # full-grid agreement (ink AND background). Rewarding matching blanks
            # is what separates '8' (ink left) from '3' (blank left); aspect-
            # preserved normalization keeps it from collapsing thin glyphs.
            matches = sum(1 for i in range(n) if vec[i] == tpl[i])
            score = matches / n
            if score > best_score:
                best_ch, best_score = ch, score
        return best_ch, best_score
