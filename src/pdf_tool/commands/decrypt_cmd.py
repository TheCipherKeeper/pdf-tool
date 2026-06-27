"""Command: pdf-tool decrypt <file> --password X -o out.pdf"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def decrypt(file: Path, out: Path, password: str) -> None:
    """Remove encryption from a PDF (requires the user/owner password)."""
    core.decrypt(file, out, password)
    safe_print(console, f"[green]Decrypted[/green]  ->  {out}")