"""Command: pdf-tool rotate <file> --angle 90 [--pages 1-3] -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def rotate(
    file: Path,
    angle: int = 90,
    pages: Optional[str] = None,
    out: Optional[Path] = None,
    password: Optional[str] = None,
) -> None:
    """Rotate selected pages (or all) by 90/180/270 degrees."""
    if angle not in (90, 180, 270):
        raise typer.BadParameter("--angle must be 90, 180, or 270.")
    if out is None:
        out = file.with_name(file.stem + ".rotated.pdf")
    n = core.rotate(file, angle, pages, out, password)
    safe_print(console, f"[green]Rotated {n} page(s) by {angle}°[/green]  ->  {out}")