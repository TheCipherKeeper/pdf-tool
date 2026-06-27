"""Command: pdf-tool watermark <file> --text "DRAFT" -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def watermark(
    file: Path,
    text: str,
    out: Optional[Path] = None,
    fontsize: int = 48,
    password: Optional[str] = None,
) -> None:
    """Stamp a diagonal text watermark on every page."""
    if out is None:
        out = file.with_name(file.stem + ".watermarked.pdf")
    n = core.watermark(file, out, text, fontsize=fontsize, password=password)
    safe_print(console, f"[green]Watermarked {n} page(s)[/green]  ->  {out}")