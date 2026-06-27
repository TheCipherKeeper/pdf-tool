"""Command: pdf-tool is-scanned <file>

Diagnoses whether a PDF is image-only (scanned) — i.e. has (near) no text
layer and is composed of page images. Reports per-page status and a verdict.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from ..core.pdf import is_scanned
from ..utils import safe_print

console = Console()


def is_scanned_cmd(
    file: Path,
    threshold: int = 10,
    password: Optional[str] = None,
) -> None:
    """Detect scanned (image-only) pages and report a verdict."""
    result = is_scanned(file, password=password, threshold=threshold)
    total = result["total"]
    scanned = set(result["scanned_pages"])

    table = Table(title=f"Scan detection: {file.name}", show_header=True, header_style="bold")
    table.add_column("Page", justify="right")
    table.add_column("Status", justify="left")
    for i in range(1, total + 1):
        status = "scanned (image-only)" if i in scanned else "has text"
        table.add_row(str(i), status)
    console.print(table)

    verdict = "SCANNED (needs OCR)" if result["is_scanned"] else "has a text layer"
    color = "yellow" if result["is_scanned"] else "green"
    scanned_count = len(scanned)
    safe_print(
        console,
        f"\n[{color}]{verdict}[/{color}] — {scanned_count}/{total} page(s) image-only.",
    )
    if result["is_scanned"]:
        safe_print(
            console,
            "[dim]Tip: run `pdf-tool text <file> --ocr-fallback` to extract text, "
            "or `pdf-tool ocr <file> -o out.pdf` to build a searchable PDF.[/dim]",
        )