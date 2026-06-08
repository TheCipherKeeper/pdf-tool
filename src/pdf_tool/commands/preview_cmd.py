"""Command: pdf-tool preview <file> [--pages 1-3] -o out_dir

Renders pages of a PDF to PNG images (uses PyMuPDF).
"""
from pathlib import Path
import re

import typer
from rich.console import Console
import fitz

from ..utils import fmt_bytes, safe_print

console = Console()

console = Console()


def preview(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out_dir: Path = typer.Option(Path("previews"), "--out", "-o"),
    pages: str = typer.Option(None, "--pages", "-p", help="Page range, e.g. 1-3,5"),
    dpi: int = typer.Option(150, "--dpi", help="Render resolution"),
    fmt: str = typer.Option("png", "--format", "-f", help="png or jpeg"),
) -> None:
    """Render pages of a PDF to images."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(file))

    if pages:
        nums = _parse_pages(pages, len(doc))
    else:
        nums = list(range(1, len(doc) + 1))

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for n in nums:
        page = doc[n - 1]
        pix = page.get_pixmap(matrix=mat)
        out_path = out_dir / f"page_{n:03d}.{fmt}"
        if fmt == "jpeg":
            pix.save(str(out_path), jpg_quality=92)
        else:
            pix.save(str(out_path))
        safe_print(console, f"  [green]OK[/green] {out_path}")

    console.print(f"\n[green]Rendered {len(nums)} pages to {out_dir}/[/green]")


def _parse_pages(spec: str, total: int) -> list[int]:
    out: list[int] = []
    for token in spec.split(","):
        token = token.strip()
        if "-" in token:
            a, b = token.split("-", 1)
            a, b = int(a), int(b)
            if a > b: a, b = b, a
            out.extend(range(a, b + 1))
        else:
            out.append(int(token))
    return [n for n in out if 1 <= n <= total]
