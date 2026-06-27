"""Command: pdf-tool ocr <file> -o out.pdf

OCR scanned PDFs into a searchable PDF with a text layer. Two engines:
  * tesseract — produces a searchable PDF natively (one subprocess per page).
  * easyocr   — recognizes text + boxes; we stamp an invisible text layer over
                a full-page image so the result is searchable.

Languages use 2-letter codes (en,ru,ja,...). Legacy tesseract specs (rus+eng)
are also accepted.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress
import fitz

from ..backends import require
from ..core.ocr import parse_langs, resolve_engine, recognize_image_with_boxes
from ..core.pdf import _open_fitz
from ..utils import parse_pages, safe_print

console = Console()


def ocr(
    file: Path,
    out: Path,
    lang: str = "en,ru",
    dpi: int = 300,
    pages: Optional[str] = None,
    engine: str = "auto",
) -> None:
    """OCR a scanned PDF and produce a searchable PDF with a text layer."""
    resolved = resolve_engine(engine)
    langs = parse_langs(lang)
    doc = _open_fitz(file)

    if pages:
        nums = parse_pages(pages, len(doc))
    else:
        nums = list(range(1, len(doc) + 1))

    out.parent.mkdir(parents=True, exist_ok=True)
    if resolved == "tesseract":
        _ocr_tesseract(doc, nums, langs, dpi, out)
    else:
        _ocr_easyocr(doc, nums, langs, dpi, out)
    doc.close()
    safe_print(console, f"[green]OCR ({resolved}) complete[/green]  ->  {out}")


def _ocr_tesseract(doc, nums, langs, dpi, out) -> None:
    """tesseract: render each page to PNG, run tesseract -> PDF, concatenate."""
    tesseract = require("tesseract")
    from ..core.ocr import tesseract_codes

    lang_arg = tesseract_codes(langs)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    tmp_dir = Path(tempfile.mkdtemp(prefix="ocr_"))
    try:
        out_doc = fitz.open()
        with Progress() as progress:
            task = progress.add_task("OCR (tesseract)…", total=len(nums))
            for n in nums:
                page = doc[n - 1]
                pix = page.get_pixmap(matrix=matrix)
                img_path = tmp_dir / f"p{n:04d}.png"
                pix.save(str(img_path))
                pdf_path = tmp_dir / f"p{n:04d}.pdf"
                subprocess.run(
                    [str(tesseract), str(img_path), str(pdf_path.with_suffix("")),
                     "-l", lang_arg, "pdf"],
                    check=True, capture_output=True,
                )
                ocr_page = fitz.open(str(pdf_path))
                out_doc.insert_pdf(ocr_page)
                ocr_page.close()
                progress.update(task, advance=1)
        out_doc.save(str(out))
        out_doc.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _ocr_easyocr(doc, nums, langs, dpi, out) -> None:
    """easyocr: stamp an invisible text layer over a full-page image per page."""
    from ..core.ocr import _get_easyocr_reader, easyocr_codes

    reader = _get_easyocr_reader(easyocr_codes(langs))
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    scale = 72.0 / dpi  # image-px -> PDF points
    tmp_dir = Path(tempfile.mkdtemp(prefix="ocr_"))
    try:
        out_doc = fitz.open()
        with Progress() as progress:
            task = progress.add_task("OCR (easyocr)…", total=len(nums))
            for n in nums:
                page = doc[n - 1]
                pix = page.get_pixmap(matrix=matrix)
                img_path = tmp_dir / f"p{n:04d}.png"
                pix.save(str(img_path))

                boxes = recognize_image_with_boxes(img_path, langs, "easyocr")
                # New page sized to the rendered image (in PDF points).
                w = pix.width * scale
                h = pix.height * scale
                new = out_doc.new_page(width=w, height=h)
                new.insert_image(new.rect, stream=pix.tobytes("png"))

                for bbox, text in boxes:
                    xs = [pt[0] for pt in bbox]
                    ys = [pt[1] for pt in bbox]
                    minx, miny = min(xs), min(ys)
                    box_h = max(ys) - min(ys)
                    x = minx * scale
                    # fitz insert_text point is the text baseline (bottom of box).
                    y = (miny + box_h) * scale
                    fontsize = max(4.0, box_h * scale * 0.85)
                    try:
                        new.insert_text(
                            fitz.Point(x, y), text,
                            fontsize=fontsize, render_mode=3, overlay=True,
                        )
                    except Exception:
                        pass
                progress.update(task, advance=1)
        out_doc.save(str(out))
        out_doc.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)