"""Command: pdf-tool preview <file> [--pages 1-3] -o out_dir

Renders pages of a PDF to PNG/JPEG images (uses PyMuPDF).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
import fitz

from ..utils import parse_pages, safe_print

console = Console()

_VALID_FMTS = {"png", "jpeg", "jpg"}


def preview(
    file: Path,
    out_dir: Path = Path("previews"),
    pages: Optional[str] = None,
    dpi: int = 150,
    fmt: str = "png",
) -> None:
    """Render pages of a PDF to images."""
    fmt = fmt.lower()
    if fmt not in _VALID_FMTS:
        raise typer.BadParameter(f"Unknown format '{fmt}'. Use one of: {', '.join(sorted(_VALID_FMTS))}")
    save_fmt = "jpeg" if fmt in ("jpeg", "jpg") else "png"

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(file))

    if pages:
        nums = parse_pages(pages, len(doc))
    else:
        nums = list(range(1, len(doc) + 1))

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for n in nums:
        page = doc[n - 1]
        pix = page.get_pixmap(matrix=mat)
        out_path = out_dir / f"page_{n:03d}.{fmt}"
        if save_fmt == "jpeg":
            pix.save(str(out_path), jpg_quality=92)
        else:
            pix.save(str(out_path))
        safe_print(console, f"  [green]OK[/green] {out_path}")

    console.print(f"\n[green]Rendered {len(nums)} pages to {out_dir}/[/green]")