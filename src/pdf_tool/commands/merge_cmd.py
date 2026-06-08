"""Command: pdf-tool merge file1.pdf file2.pdf ... -o out.pdf"""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from pypdf import PdfReader, PdfWriter

from ..utils import fmt_bytes, safe_print

console = Console()


def merge(
    files: list[Path] = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out", "-o"),
    bookmarks: bool = typer.Option(True, "--bookmarks/--no-bookmarks", help="Add bookmarks from filenames"),
) -> None:
    """Merge multiple PDFs into one."""
    writer = PdfWriter()
    # Add a top-level outline entry per file (bookmark)
    if bookmarks:
        writer.add_outline_item("Merged PDFs", 0)  # optional root
    for f in files:
        reader = PdfReader(str(f))
        first_page_in_out = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)
        if bookmarks:
            writer.add_outline_item(f.stem, first_page_in_out)
    with open(out, "wb") as fp:
        writer.write(fp)
    safe_print(console, f"[green]Merged {len(files)} files[/green]  ->  {out}  ({fmt_bytes(out.stat().st_size)})")
