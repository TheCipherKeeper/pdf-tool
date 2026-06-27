"""Command: pdf-tool repair <file> -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def repair(file: Path, out: Optional[Path] = None) -> None:
    """Recover a damaged PDF using pikepdf/qpdf."""
    if out is None:
        out = file.with_name(file.stem + ".repaired.pdf")
    core.repair(file, out)
    safe_print(console, f"[green]Repaired[/green]  ->  {out}")