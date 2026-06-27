"""Command: pdf-tool merge file1.pdf file2.pdf ... -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from pypdf import PdfReader, PdfWriter

from ..core.pdf import open_reader
from ..utils import fmt_bytes, safe_print

console = Console()


def merge(
    files: list[Path],
    out: Path,
    bookmarks: bool = True,
    password: Optional[str] = None,
) -> None:
    """Merge multiple PDFs into one, adding a parent bookmark per source file."""
    if len(files) < 2:
        raise typer.BadParameter("Need at least two files to merge.")

    writer = PdfWriter()
    parent_outline = None
    if bookmarks:
        # Reserve a top-level parent entry that per-file bookmarks attach to.
        parent_outline = writer.add_outline_item("Merged PDFs", 0)

    used_titles: set[str] = set()
    for f in files:
        reader = open_reader(f, password)
        first_page_in_out = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)
        if bookmarks:
            title = f.stem
            # Dedupe duplicate stems so each bookmark is uniquely navigable.
            base, n = title, 1
            while title in used_titles:
                n += 1
                title = f"{base} ({n})"
            used_titles.add(title)
            writer.add_outline_item(title, first_page_in_out, parent=parent_outline)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fp:
        writer.write(fp)
    safe_print(
        console,
        f"[green]Merged {len(files)} files[/green]  ->  {out}  "
        f"({fmt_bytes(out.stat().st_size)})",
    )