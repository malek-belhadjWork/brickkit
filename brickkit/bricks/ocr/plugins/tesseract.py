"""tesseract OCR plugin (real, free, local). Heavy imports are deferred into the
factory so a client using a different OCR engine never needs pytesseract.

Config params (all optional):
  cmd            path to tesseract.exe (Windows installs are often not on PATH;
                 if omitted, common install locations are auto-detected)
  lang           language(s), e.g. "eng" (default) or "eng+deu"
  psm            page segmentation mode; 7 = single text line (default), good for
                 the small zonal crops extract produces
  oem            OCR engine mode (default 3 = LSTM)
  char_whitelist restrict recognized characters, e.g. "0123456789.,-" — a large
                 accuracy win for numeric / ID fields
"""
from __future__ import annotations

import os
import shutil

from ..registry import REGISTRY

_WINDOWS_GUESSES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _resolve_cmd(cmd):
    if cmd:
        return cmd
    if shutil.which("tesseract"):
        return None  # already on PATH; let pytesseract use its default
    for guess in _WINDOWS_GUESSES:
        if os.path.exists(guess):
            return guess
    return None


@REGISTRY.register("tesseract")
def make_tesseract(lang="eng", psm=7, oem=3, char_whitelist=None, cmd=None):
    import pytesseract
    from pytesseract import Output

    resolved = _resolve_cmd(cmd)
    if resolved:
        pytesseract.pytesseract.tesseract_cmd = resolved

    default_whitelist = char_whitelist  # factory-level default

    def _config(whitelist):
        cfg = f"--oem {oem} --psm {psm}"
        if whitelist:
            cfg += f" -c tessedit_char_whitelist={whitelist}"
        return cfg

    def run(image, char_whitelist=None, **_):
        # a field's `chars` (per call) overrides the factory default whitelist
        config = _config(char_whitelist or default_whitelist)
        data = pytesseract.image_to_data(
            image, lang=lang, config=config, output_type=Output.DICT
        )
        words, confs = [], []
        for word, conf in zip(data["text"], data["conf"]):
            word = word.strip()
            if not word:
                continue
            try:
                c = float(conf)
            except (TypeError, ValueError):
                continue
            if c < 0:  # tesseract uses -1 for non-text blocks
                continue
            words.append(word)
            confs.append(c / 100.0)  # normalize 0..100 -> 0..1
        text = " ".join(words)
        confidence = sum(confs) / len(confs) if confs else 0.0
        return text, confidence

    return run
