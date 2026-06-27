"""Command: pdf-tool docx merge a.docx b.docx -o out.docx"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from ..core import docx as core
from ..utils import fmt_bytes, safe_print

console = Console()


def merge(files: list[Path], out: Path) -> None:
    """Merge multiple .docx files into one."""
    if len(files) < 2:
        raise typer.BadParameter("Need at least two .docx files to merge.")
    n = core.docx_merge(files, out)
    safe_print(
        console,
        f"[green]Merged {n} .docx files[/green]  ->  {out}  "
        f"({fmt_bytes(out.stat().st_size)})",
    )