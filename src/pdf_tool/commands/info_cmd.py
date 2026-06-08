"""Command: pdf-tool info <file>"""
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from pypdf import PdfReader

from ..utils import fmt_bytes

console = Console()


def info(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    show_fonts: bool = typer.Option(False, "--fonts", help="List embedded fonts"),
) -> None:
    """Show metadata and structure of a PDF."""
    reader = PdfReader(str(file))
    meta = reader.metadata or {}
    n_pages = len(reader.pages)
    enc = "yes" if reader.is_encrypted else "no"

    console.print(f"\n[bold]{file.name}[/bold]  [dim]({fmt_bytes(file.stat().st_size)})[/dim]")
    console.print(f"  Pages:        {n_pages}")
    console.print(f"  Encrypted:    {enc}")
    if meta:
        for k, v in meta.items():
            console.print(f"  {str(k).strip('/'):<14} {v}")

    # Image count per page
    img_table = Table(title="Images per page", show_header=True, header_style="bold")
    img_table.add_column("Page", justify="right")
    img_table.add_column("Images", justify="right")
    img_table.add_column("Total size", justify="right")

    total_imgs = 0
    total_size = 0
    for i, page in enumerate(reader.pages, start=1):
        xobjs = page.get("/Resources", {}).get("/XObject", {})
        count = sum(1 for o in xobjs.values() if o.get_object().get("/Subtype") == "/Image")
        size = 0
        for o in xobjs.values():
            try:
                o = o.get_object()
                if o.get("/Subtype") != "/Image":
                    continue
                size += len(o.get_data() or b"")
            except Exception:
                pass
        total_imgs += count
        total_size += size
        if count:
            img_table.add_row(str(i), str(count), fmt_bytes(size))
    console.print(img_table)
    console.print(f"  [bold]Total:[/bold] {total_imgs} images, {fmt_bytes(total_size)}")

    if show_fonts:
        fonts: set[str] = set()
        for page in reader.pages:
            res = page.get("/Resources", {})
            for f in res.get("/Font", {}).values():
                try:
                    fonts.add(f.get_object().get("/BaseFont", "?"))
                except Exception:
                    pass
        if fonts:
            console.print(f"\n  [bold]Fonts ({len(fonts)}):[/bold]")
            for f in sorted(fonts):
                console.print(f"    - {f}")
