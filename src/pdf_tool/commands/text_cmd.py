"""Command: pdf-tool text <file>

Extracts text. Uses poppler's pdftotext when available; falls back to pypdf.
Page selection supports discrete ranges (1,8,11-13) — when a non-contiguous
range is requested we render just those pages with PyMuPDF into a temp PDF
first, so pdftotext truly sees only the selected pages.

With --ocr-fallback, pages that have (near) no text layer but contain an
image (i.e. scanned pages) are routed through tesseract automatically so the
returned text includes machine-vision-recognized content.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..backends import BIN
from ..core.ocr import parse_langs
from ..core.pdf import open_reader, text_with_ocr_fallback
from ..utils import parse_pages, safe_print

console = Console()


def text(
    file: Path,
    layout: bool = False,
    out: Optional[Path] = None,
    pages: Optional[str] = None,
    password: Optional[str] = None,
    ocr_fallback: bool = False,
    engine: str = "auto",
    lang: str = "en,ru",
    ocr_dpi: int = 300,
    ocr_threshold: int = 10,
) -> None:
    """Extract text from a PDF."""
    # Determine selected page numbers (1-based) if a spec was given.
    reader = open_reader(file, password)
    total = len(reader.pages)
    selected = parse_pages(pages, total, allow_empty=True) if pages else None

    if ocr_fallback:
        # Machine-vision path: per-page text, OCR-ing scanned pages.
        pages_text, stats = text_with_ocr_fallback(
            file, selected,
            langs=parse_langs(lang),
            engine=engine,
            dpi=ocr_dpi,
            threshold=ocr_threshold,
            password=password,
        )
        text_data = "\n".join(pages_text)
        _report_ocr_stats(stats)
    else:
        text_data = _extract(file, reader, layout, selected)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text_data.encode("utf-8"))
        console.print(f"[green]Wrote text to {out}[/green]")
    else:
        console.print(text_data, end="")


def _report_ocr_stats(stats: dict) -> None:
    """Print a summary of the OCR-fallback run (only if something notable)."""
    ocr = stats["ocr_pages"]
    skipped = stats.get("skipped_no_engine", 0)
    errors = stats.get("ocr_errors", 0)
    engine = stats.get("engine", "?")
    if ocr:
        safe_print(console, f"[dim]OCR ({engine}) applied to {ocr} scanned page(s).[/dim]")
    if skipped:
        safe_print(
            console,
            f"[yellow]Warning: {skipped} scanned page(s) had no recoverable text "
            f"and no OCR engine is available. Install easyocr (`uv pip install -e "
            f"\".[ocr]\"`) or tesseract.[/yellow]",
        )
    if errors:
        last = stats.get("last_error", "")
        safe_print(
            console,
            f"[yellow]Warning: {engine} produced no text on {errors} page(s)"
            + (f" — {last}" if last else "")
            + ". Check language data / engine install.[/yellow]",
        )


def _extract(
    file: Path, reader, layout: bool, selected: Optional[list[int]]
) -> str:
    """Pick the best available extractor and return text (no OCR)."""
    if BIN.pdftotext is None:
        # Fallback: pypdf text extraction (no external binary needed).
        return _pypdf_text(reader, selected)

    src, is_temp = _materialize_pages(file, reader, selected)
    try:
        return _pdftotext(src, layout)
    finally:
        if is_temp:
            src.unlink(missing_ok=True)


def _pdftotext(src: Path, layout: bool) -> str:
    args = [str(BIN.pdftotext)]
    if layout:
        args.append("-layout")
    args += [str(src), "-"]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr}")
    return result.stdout


def _materialize_pages(
    file: Path, reader, selected: Optional[list[int]]
) -> tuple[Path, bool]:
    """Return (path, is_temp) to a PDF containing only the selected pages.

    If no selection or the selection covers the whole document, we use the
    original file directly (is_temp=False). Otherwise a subset is written to a
    temp PDF so pdftotext truly sees only the chosen pages (is_temp=True).
    """
    if selected is None:
        return file, False

    total = len(reader.pages)
    if selected == list(range(1, total + 1)):
        return file, False

    from pypdf import PdfWriter
    import os

    writer = PdfWriter()
    for n in selected:
        writer.add_page(reader.pages[n - 1])
    fd, tmp_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)  # release the OS handle so we can reopen for writing
    tmp = Path(tmp_name)
    with open(tmp, "wb") as f:
        writer.write(f)
    return tmp, True


def _pypdf_text(reader, selected: Optional[list[int]]) -> str:
    """Extract text via pypdf (no poppler)."""
    idxs = selected if selected is not None else list(range(1, len(reader.pages) + 1))
    parts: list[str] = []
    for n in idxs:
        try:
            parts.append(reader.pages[n - 1].extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)