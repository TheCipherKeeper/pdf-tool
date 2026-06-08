"""Command: pdf-tool images <file> [--extract]"""
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
import fitz  # PyMuPDF

from ..utils import fmt_bytes

console = Console()


def images(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    extract: bool = typer.Option(False, "--extract", "-e", help="Extract images to a directory"),
    out_dir: Path = typer.Option(Path("images"), "--out", "-o", help="Output directory for extraction"),
    min_size: int = typer.Option(0, "--min-size", help="Skip images smaller than N bytes"),
) -> None:
    """List (or extract) all images embedded in the PDF."""
    doc = fitz.open(str(file))
    n_pages = len(doc)

    rows: list[tuple[int, str, int, int, int, str]] = []
    # rows: (page, xref, w, h, size, ext)

    if extract:
        out_dir.mkdir(parents=True, exist_ok=True)
        saved = 0
        for page_idx in range(n_pages):
            for img in doc[page_idx].get_images(full=True):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.size < min_size:
                    pix = None
                    continue
                ext = "png"
                if pix.colorspace and pix.colorspace.name == "DeviceRGB":
                    ext = "png"
                elif pix.colorspace and pix.colorspace.name == "DeviceGray":
                    ext = "png"
                # Use extract_image for proper format detection
                img_info = doc.extract_image(xref)
                ext = img_info["ext"]
                data = img_info["image"]
                if len(data) < min_size:
                    continue
                out_path = out_dir / f"page{page_idx+1:03d}_xref{xref}.{ext}"
                out_path.write_bytes(data)
                saved += 1
                rows.append((page_idx + 1, str(xref), img_info["width"], img_info["height"], len(data), ext))
        console.print(f"[green]Extracted {saved} images to {out_dir}/[/green]")
    else:
        for page_idx in range(n_pages):
            for img in doc[page_idx].get_images(full=True):
                xref = img[0]
                img_info = doc.extract_image(xref)
                rows.append((page_idx + 1, str(xref), img_info["width"], img_info["height"], len(img_info["image"]), img_info["ext"]))

    if not extract:
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
