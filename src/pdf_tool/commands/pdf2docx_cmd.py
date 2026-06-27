"""Command: pdf-tool pdf2docx <file.pdf> -o out.docx (via LibreOffice, lossy)"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import docx as core
from ..utils import safe_print

console = Console()


def pdf2docx(file: Path, out: Optional[Path] = None) -> None:
    """Convert a PDF to .docx using LibreOffice headless.

    Note: PDF→docx conversion is inherently lossy. LibreOffice rebuilds a
    flowable document from the PDF page layout, so complex layouts, fonts,
    and vector graphics may not transfer faithfully.
    """
    if out is None:
        out = file.with_suffix(".docx")
    core.libreoffice_convert(file, 'docx:"MS Word 2007 XML"', out)
    safe_print(console, f"[green]Converted to DOCX (lossy)[/green]  ->  {out}")