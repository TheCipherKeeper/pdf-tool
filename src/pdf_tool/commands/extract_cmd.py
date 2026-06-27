"""Command: pdf-tool extract <file> --pages 1-5 -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def extract(
    file: Path,
    pages: str,
    out: Optional[Path] = None,
    password: Optional[str] = None,
) -> None:
    """Extract a page range into a new PDF."""
    if out is None:
        out = file.with_name(file.stem + ".extract.pdf")
    n = core.extract(file, pages, out, password)
    safe_print(console, f"[green]Extracted {n} page(s)[/green]  ->  {out}")