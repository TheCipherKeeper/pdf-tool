"""Command: pdf-tool info <file>"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from pypdf import PdfReader

from ..core.pdf import open_reader
from ..utils import fmt_bytes

console = Console()


def _resolved(obj):
    """Resolve a pypdf indirect object to its underlying value, best-effort."""
    try:
        return obj.get_object()
    except Exception:
        return obj


def info(
    file: Path,
    show_fonts: bool = False,
    password: Optional[str] = None,
) -> None:
    """Show metadata and structure of a PDF."""
    reader = open_reader(file, password)
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
        try:
            res = _resolved(page.get("/Resources", {}))
            xobjs = _resolved(res.get("/XObject", {})) if res else {}
        except Exception:
            xobjs = {}
        count = 0
        size = 0
        try:
            for o in xobjs.values():
                oo = _resolved(o)
                if oo.get("/Subtype") == "/Image":
                    count += 1
                    try:
                        size += len(oo.get_data() or b"")
                    except Exception:
                        pass
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
            try:
                res = _resolved(page.get("/Resources", {}))
                for f in _resolved(res.get("/Font", {})).values():
                    fonts.add(_resolved(f).get("/BaseFont", "?"))
            except Exception:
                pass
        if fonts:
            console.print(f"\n  [bold]Fonts ({len(fonts)}):[/bold]")
            for f in sorted(fonts):
                console.print(f"    - {f}")