"""Command: pdf-tool rearrange file.pdf --pages 1,3-5,2 -o out.pdf

Reorder, remove, or duplicate pages.
"""
from pathlib import Path
import re

import typer
from rich.console import Console
from pypdf import PdfReader, PdfWriter

from ..utils import fmt_bytes, safe_print

console = Console()


def _parse_pages(spec: str, total: int) -> list[int]:
    """Parse '1,3-5,7' into 0-based page indices [0, 2, 3, 4, 6]."""
    out: list[int] = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a
            for p in range(a, b + 1):
                if not (1 <= p <= total):
                    raise ValueError(f"Page {p} out of range (1..{total})")
                out.append(p - 1)
        else:
            p = int(token)
            if not (1 <= p <= total):
                raise ValueError(f"Page {p} out of range (1..{total})")
            out.append(p - 1)
    return out


def rearrange(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    pages: str = typer.Option(..., "--pages", "-p", help="Page order, e.g. 1,3-5,2"),
    out: Path = typer.Option(..., "--out", "-o"),
) -> None:
    """Rearrange (reorder/remove/duplicate) pages in a PDF."""
    reader = PdfReader(str(file))
    total = len(reader.pages)
    indices = _parse_pages(pages, total)

    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])

    with open(out, "wb") as f:
        writer.write(f)
    safe_print(console, f"[green]Wrote {len(indices)} pages[/green]  ->  {out}")
