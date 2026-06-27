"""Pluggable OCR engines with a unified API.

Backends:
  * easyocr  — pure-Python (PyTorch); languages ship as pip-installable model
              packs that download automatically. No external binary, no
              TESSDATA_PREFIX. Install with `uv pip install -e ".[ocr]"`.
  * tesseract — external binary; fast, but needs language data on disk.

Languages are specified with 2-letter canonical codes (`en,ru,ja`) and mapped
to each engine's own codes. Legacy tesseract specs (`rus+eng`) are also accepted.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# canonical code -> (tesseract_code, easyocr_code)
LANGS: dict[str, tuple[str, str]] = {
    "en": ("eng", "en"),
    "ru": ("rus", "ru"),
    "ja": ("jpn", "ja"),
    "ko": ("kor", "ko"),
    "zh": ("chi_sim", "ch_sim"),
    "de": ("deu", "de"),
    "fr": ("fra", "fr"),
    "es": ("spa", "es"),
    "it": ("ita", "it"),
    "pt": ("por", "pt"),
    "uk": ("ukr", "uk"),
    "pl": ("pol", "pl"),
    "nl": ("nld", "nl"),
    "tr": ("tur", "tr"),
    "ar": ("ara", "ar"),
    "hi": ("hin", "hi"),
    "cs": ("ces", "cs"),
    "sv": ("swe", "sv"),
    "th": ("tha", "th"),
    "vi": ("vie", "vi"),
}

_TESS_TO_CANON = {v[0]: k for k, v in LANGS.items()}


def parse_langs(spec: Optional[str]) -> list[str]:
    """Parse a language spec into a list of canonical codes.

    Accepts `en,ru,ja`, legacy `rus+eng`, or a single code. Defaults to en,ru.
    Unknown codes pass through (best-effort) so users aren't blocked by the map.
    """
    if not spec:
        return ["en", "ru"]
    out: list[str] = []
    for tok in spec.replace("+", ",").split(","):
        tok = tok.strip().lower()
        if not tok:
            continue
        if tok in _TESS_TO_CANON:        # tesseract 3-letter -> canonical
            out.append(_TESS_TO_CANON[tok])
        elif tok in LANGS:               # already canonical
            out.append(tok)
        else:                            # unknown -> passthrough
            out.append(tok)
    return out or ["en", "ru"]


def tesseract_codes(langs: list[str]) -> str:
    return "+".join(LANGS.get(l, (l, l))[0] for l in langs)


def easyocr_codes(langs: list[str]) -> list[str]:
    return [LANGS.get(l, (l, l))[1] for l in langs]


def available_engines() -> list[str]:
    """Engines actually usable in this environment (easyocr first)."""
    engs: list[str] = []
    try:
        import easyocr  # noqa: F401

        engs.append("easyocr")
    except Exception:
        pass
    from ..backends import BIN

    if BIN.tesseract is not None:
        engs.append("tesseract")
    return engs


def resolve_engine(engine: str) -> str:
    """Validate/auto-pick an engine. Raises a clear error if none usable."""
    avail = available_engines()
    if engine == "auto":
        if "easyocr" in avail:
            return "easyocr"
        if "tesseract" in avail:
            return "tesseract"
        raise RuntimeError(
            "No OCR engine available. Install easyocr (`uv pip install -e \".[ocr]\"`) "
            "or install tesseract with language data."
        )
    if engine not in avail:
        raise RuntimeError(
            f"OCR engine '{engine}' not available. Available: "
            f"{', '.join(avail) or 'none'}."
        )
    return engine


def _ensure_utf8_stdout() -> None:
    """easyocr's progress bar uses Unicode block chars that crash the default
    Windows cp1252 console. Reconfigure stdout to utf-8 so it can print."""
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# easyocr Reader instances are expensive (load + cache models). Keep one per
# language set for the lifetime of the process.
_EASYOCR_READERS: dict[tuple[str, ...], object] = {}


def _get_easyocr_reader(codes: list[str]):
    import warnings

    import easyocr

    key = tuple(codes)
    if key not in _EASYOCR_READERS:
        _ensure_utf8_stdout()
        # easyocr/torch emit noisy Deprecation/User warnings on import & run.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _EASYOCR_READERS[key] = easyocr.Reader(list(codes), gpu=False)
    return _EASYOCR_READERS[key]


def recognize_image(image_path: Path, langs: list[str], engine: str) -> str:
    """Recognize text in an image file. Returns the joined text."""
    import warnings

    engine = resolve_engine(engine)
    if engine == "easyocr":
        reader = _get_easyocr_reader(easyocr_codes(langs))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = reader.readtext(str(image_path), detail=0)
        return "\n".join(str(x) for x in result)
    # tesseract
    from ..backends import BIN

    return _tesseract_text(image_path, tesseract_codes(langs), BIN.tesseract)


def recognize_image_with_boxes(image_path: Path, langs: list[str], engine: str):
    """Recognize text with bounding boxes, for building searchable PDFs.

    Returns a list of (bbox_px, text) where bbox_px is a list of 4 [x,y] points
    in image-pixel coordinates (top-left origin).
    """
    import warnings

    engine = resolve_engine(engine)
    if engine == "easyocr":
        reader = _get_easyocr_reader(easyocr_codes(langs))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = reader.readtext(str(image_path), detail=1)
        return [(b, t) for (b, t, _c) in result]
    # tesseract: produce word-level boxes via TSV.
    from ..backends import BIN

    return _tesseract_boxes(image_path, tesseract_codes(langs), BIN.tesseract)


def _tesseract_text(image_path: Path, lang: str, tesseract) -> str:
    fd, base = tempfile.mkstemp()
    os.close(fd)
    txt = Path(base + ".txt")
    try:
        r = subprocess.run(
            [str(tesseract), str(image_path), base, "-l", lang, "txt"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return ""
        if txt.exists():
            return txt.read_text(encoding="utf-8", errors="replace")
        return ""
    finally:
        for p in (base, str(txt)):
            try:
                os.unlink(p)
            except OSError:
                pass


def _tesseract_boxes(image_path: Path, lang: str, tesseract):
    """Word boxes via tesseract TSV output."""
    import csv
    import io

    fd, base = tempfile.mkstemp()
    os.close(fd)
    tsv = Path(base + ".tsv")
    try:
        r = subprocess.run(
            [str(tesseract), str(image_path), base, "-l", lang, "tsv"],
            capture_output=True, text=True,
        )
        if r.returncode != 0 or not tsv.exists():
            return []
        boxes = []
        with open(tsv, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                txt = (row.get("text") or "").strip()
                conf = row.get("conf", "-1")
                if not txt or conf == "-1":
                    continue
                try:
                    left = int(row["left"]); top = int(row["top"])
                    w = int(row["width"]); h = int(row["height"])
                except (KeyError, ValueError):
                    continue
                bbox = [[left, top], [left + w, top], [left + w, top + h], [left, top + h]]
                boxes.append((bbox, txt))
        return boxes
    finally:
        for p in (base, str(tsv)):
            try:
                os.unlink(p)
            except OSError:
                pass