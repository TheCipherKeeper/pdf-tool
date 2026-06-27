"""Command: pdf-tool docx text <file.docx> [-o out.txt]"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import docx as core

console = Console()


def text(file: Path, out: Optional[Path] = None) -> None:
    """Extract text from a .docx file (paragraphs + tables)."""
    data = core.docx_text(file)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(data, encoding="utf-8")
        console.print(f"[green]Wrote text to {out}[/green]")
    else:
        console.print(data, end="")