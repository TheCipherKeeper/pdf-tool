"""Command: pdf-tool text <file>

Extracts text. Uses poppler's pdftotext when available; falls back to pypdf.
Page selection supports discrete ranges (1,8,11-13) — when a non-contiguous
range is requested we render just those pages with PyMuPDF into a temp PDF
first, so pdftotext truly sees only the selected pages.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..backends import BIN
from ..core.pdf import open_reader
from ..utils import parse_pages

console = Console()


def text(
    file: Path,
    layout: bool = False,
    out: Optional[Path] = None,
    pages: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Extract text from a PDF."""
    # Determine selected page numbers (1-based) if a spec was given.
    reader = open_reader(file, password)
    total = len(reader.pages)
    selected = parse_pages(pages, total, allow_empty=True) if pages else None

    text_data = _extract(file, reader, layout, selected)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text_data.encode("utf-8"))
        console.print(f"[green]Wrote text to {out}[/green]")
    else:
        console.print(text_data, end="")


def _extract(
    file: Path, reader, layout: bool, selected: Optional[list[int]]
) -> str:
    """Pick the best available extractor and return text."""
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