"""Command: pdf-tool images <file> [--extract]"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table
import fitz  # PyMuPDF

from ..utils import fmt_bytes

console = Console()


def images(
    file: Path,
    extract: bool = False,
    out_dir: Path = Path("images"),
    min_size: int = 0,
) -> None:
    """List (or extract) all images embedded in the PDF.

    Uses `doc.extract_image(xref)` exclusively — it returns the raw encoded
    bytes and the correct extension for every colorspace (RGB/Gray/CMYK/...),
    so we avoid `fitz.Pixmap` which throws on non-RGB/Gray images.
    """
    doc = fitz.open(str(file))
    n_pages = len(doc)

    rows: list[tuple[int, str, int, int, int, str]] = []
    saved = 0

    if extract:
        out_dir.mkdir(parents=True, exist_ok=True)

    for page_idx in range(n_pages):
        for img in doc[page_idx].get_images(full=True):
            xref = img[0]
            try:
                img_info = doc.extract_image(xref)
            except Exception as e:
                console.print(f"[yellow]  skip xref {xref} on page {page_idx+1}: {e}[/yellow]")
                continue
            data = img_info["image"]
            width = img_info["width"]
            height = img_info["height"]
            ext = img_info["ext"]
            size = len(data)
            if size < min_size:
                continue
            if extract:
                out_path = out_dir / f"page{page_idx+1:03d}_xref{xref}.{ext}"
                out_path.write_bytes(data)
                saved += 1
            rows.append((page_idx + 1, str(xref), width, height, size, ext))

    if extract:
        console.print(f"[green]Extracted {saved} images to {out_dir}/[/green]")

    table = Table(title=f"Images in {file.name}", show_header=True, header_style="bold")
    table.add_column("Page", justify="right")
    table.add_column("XRef", justify="right")
    table.add_column("Width", justify="right")
    table.add_column("Height", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Format", justify="center")
    for r in rows:
        table.add_row(str(r[0]), r[1], str(r[2]), str(r[3]), fmt_bytes(r[4]), r[5])
    console.print(table)
    total = sum(r[4] for r in rows)
    console.print(f"\n[bold]Total:[/bold] {len(rows)} images, {fmt_bytes(total)}")