"""Command: pdf-tool rearrange file.pdf --pages 1,3-5,2 -o out.pdf

Reorder, remove, or duplicate pages.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pypdf import PdfWriter

from ..core.pdf import open_reader
from ..utils import parse_pages, safe_print

from rich.console import Console

console = Console()


def rearrange(
    file: Path,
    pages: str,
    out: Path,
    password: Optional[str] = None,
) -> None:
    """Rearrange (reorder/remove/duplicate) pages in a PDF."""
    reader = open_reader(file, password)
    total = len(reader.pages)
    nums = parse_pages(pages, total)

    writer = PdfWriter()
    for n in nums:
        writer.add_page(reader.pages[n - 1])

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    safe_print(console, f"[green]Wrote {len(nums)} pages[/green]  ->  {out}")