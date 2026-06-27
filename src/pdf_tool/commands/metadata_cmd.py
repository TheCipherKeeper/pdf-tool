"""Command: pdf-tool metadata <file> [--title ... --author ... | --strip] -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def metadata(
    file: Path,
    out: Optional[Path] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
    strip: bool = False,
    password: Optional[str] = None,
) -> None:
    """Set or strip document metadata (Title/Author/Subject/Keywords)."""
    if not strip and not any(v is not None for v in (title, author, subject, keywords)):
        raise typer.BadParameter(
            "Nothing to do. Provide --title/--author/--subject/--keywords or --strip."
        )
    if out is None:
        out = file.with_name(file.stem + ".meta.pdf")
    core.set_metadata(
        file, out,
        title=title, author=author, subject=subject, keywords=keywords,
        strip=strip, password=password,
    )
    if strip:
        safe_print(console, f"[green]Stripped metadata[/green]  ->  {out}")
    else:
        safe_print(console, f"[green]Updated metadata[/green]  ->  {out}")