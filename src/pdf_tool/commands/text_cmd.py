"""Command: pdf-tool text <file>"""
from pathlib import Path
import subprocess

import typer
from rich.console import Console

from ..backends import BIN

console = Console()


def text(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    layout: bool = typer.Option(False, "--layout", "-l", help="Preserve layout (use poppler's -layout)"),
    out: Path = typer.Option(None, "--out", "-o", help="Write to file instead of stdout"),
    pages: str = typer.Option(None, "--pages", "-p", help="Page range, e.g. 1-5,8,11-13"),
) -> None:
    """Extract text from a PDF (via poppler's pdftotext if available)."""
    if BIN.pdftotext is None:
        raise RuntimeError(
            "pdftotext (poppler) not found. Install poppler or use 'pypdf' as a fallback.\n"
            "On Windows: download poppler from https://github.com/oschwartz10612/poppler-windows"
        )
    args = [str(BIN.pdftotext)]
    if layout:
        args.append("-layout")
    if pages:
        args += ["-f", str(_first(pages)), "-l", str(_last(pages))]
    args.append(str(file))
    if out:
        args.append(str(out))
    # If no -o, poppler writes to stdout when "-" is last arg
    elif "-" not in args:
        args.append("-")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr}")
    if out is None:
        console.print(result.stdout, end="")
    else:
        console.print(f"[green]Wrote text to {out}[/green]")


def _first(spec: str) -> int:
    return int(spec.split("-")[0].split(",")[0])


def _last(spec: str) -> int:
    # last page of last range: e.g. "1-5,8,11-13" → 13
    return int(spec.rsplit("-", 1)[-1].rsplit(",", 1)[-1])
