"""Command: pdf-tool ocr <file> -o out.pdf

OCR scanned PDFs (no text layer) via tesseract: render each page to
PNG with PyMuPDF, run tesseract, and produce a searchable PDF.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress
import fitz

from ..backends import require
from ..utils import parse_pages, safe_print

console = Console()


def ocr(
    file: Path,
    out: Path,
    lang: str = "rus+eng",
    dpi: int = 300,
    pages: Optional[str] = None,
) -> None:
    """OCR a scanned PDF and produce a searchable PDF with a text layer."""
    tesseract = require("tesseract")
    doc = fitz.open(str(file))

    if pages:
        nums = parse_pages(pages, len(doc))
    else:
        nums = list(range(1, len(doc) + 1))

    out_doc = fitz.open()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    tmp_dir = out.parent / f".ocr_tmp_{out.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        with Progress() as progress:
            task = progress.add_task("OCR…", total=len(nums))
            for n in nums:
                page = doc[n - 1]
                pix = page.get_pixmap(matrix=mat)
                img_path = tmp_dir / f"page_{n:03d}.png"
                pix.save(str(img_path))

                # Run tesseract → PDF (it appends .pdf to the output base name)
                pdf_path = tmp_dir / f"page_{n:03d}.pdf"
                subprocess.run(
                    [str(tesseract), str(img_path), str(pdf_path.with_suffix("")),
                     "-l", lang, "pdf"],
                    check=True, capture_output=True,
                )
                ocr_page = fitz.open(str(pdf_path))
                out_doc.insert_pdf(ocr_page)
                ocr_page.close()
                progress.update(task, advance=1)

        out.parent.mkdir(parents=True, exist_ok=True)
        out_doc.save(str(out))
        out_doc.close()
    finally:
        out_doc.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)
    safe_print(console, f"[green]OCR complete[/green]  ->  {out}")