"""Command: pdf-tool ocr <file> -o out.pdf

OCR scanned PDFs (no text layer) via tesseract: render each page to
PNG with PyMuPDF, run tesseract, and produce a searchable PDF.
"""
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress
import fitz

from ..backends import require
from ..utils import safe_print

console = Console()


def ocr(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out", "-o"),
    lang: str = typer.Option("rus+eng", "--lang", "-l", help="tesseract language code"),
    dpi: int = typer.Option(300, "--dpi", help="Render DPI for OCR"),
    pages: str = typer.Option(None, "--pages", "-p", help="Limit to a page range"),
) -> None:
    """OCR a scanned PDF and produce a searchable PDF with a text layer."""
    tesseract = require("tesseract")
    doc = fitz.open(str(file))

    if pages:
        nums = _parse_pages(pages, len(doc))
    else:
        nums = list(range(1, len(doc) + 1))

    out_doc = fitz.open()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    tmp_dir = out.parent / f".ocr_tmp_{out.stem}"
    tmp_dir.mkdir(exist_ok=True)

    with Progress() as progress:
        task = progress.add_task("OCR…", total=len(nums))
        for n in nums:
            page = doc[n - 1]
            pix = page.get_pixmap(matrix=mat)
            img_path = tmp_dir / f"page_{n:03d}.png"
            pix.save(str(img_path))

            # Run tesseract → PDF
            pdf_path = tmp_dir / f"page_{n:03d}.pdf"
            import subprocess
            subprocess.run(
                [str(tesseract), str(img_path), str(pdf_path.with_suffix("")), "-l", lang, "pdf"],
                check=True, capture_output=True,
            )
            ocr_page = fitz.open(str(pdf_path))
            out_doc.insert_pdf(ocr_page)
            ocr_page.close()
            progress.update(task, advance=1)

    out_doc.save(str(out))
    out_doc.close()

    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    safe_print(console, f"[green]OCR complete[/green]  ->  {out}")


def _parse_pages(spec: str, total: int) -> list[int]:
    out: list[int] = []
    for token in spec.split(","):
        token = token.strip()
        if "-" in token:
            a, b = token.split("-", 1)
            a, b = int(a), int(b)
            if a > b: a, b = b, a
            out.extend(range(a, b + 1))
        else:
            out.append(int(token))
    return [n for n in out if 1 <= n <= total]
