"""Command: pdf-tool delete <file> --pages 3,7 -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def delete(
    file: Path,
    pages: str,
    out: Optional[Path] = None,
    password: Optional[str] = None,
) -> None:
    """Remove the given pages from a PDF."""
    if out is None:
        out = file.with_name(file.stem + ".deleted.pdf")
    n = core.delete(file, pages, out, password)
    safe_print(console, f"[green]Removed {n} page(s)[/green]  ->  {out}")