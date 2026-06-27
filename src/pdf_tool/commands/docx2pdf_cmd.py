"""Command: pdf-tool docx2pdf <file.docx> -o out.pdf (via LibreOffice)"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import docx as core
from ..utils import safe_print

console = Console()


def docx2pdf(file: Path, out: Optional[Path] = None) -> None:
    """Convert a .docx file to PDF using LibreOffice headless."""
    if out is None:
        out = file.with_suffix(".pdf")
    core.libreoffice_convert(file, "pdf", out)
    safe_print(console, f"[green]Converted to PDF[/green]  ->  {out}")