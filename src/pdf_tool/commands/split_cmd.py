"""Command: pdf-tool split <file> --parts N --max-size 4MB

Splits a PDF into N parts, each <= max-size, picking the highest
ghostscript quality that fits.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from pypdf import PdfReader, PdfWriter

from ..backends import BIN, require
from ..utils import fmt_bytes

console = Console()

QUALITY_LADDER = [
    (95, 300), (92, 300), (90, 300), (90, 250), (90, 200),
    (88, 200), (85, 200), (85, 180), (85, 160), (85, 150),
    (82, 150), (80, 150), (80, 130), (78, 130), (75, 120),
]


def _gs_repack(src: Path, dst: Path, jpeg_q: int, dpi: int) -> None:
    gs = require("gs")
    args = [
        str(gs), "-dNOPAUSE", "-dBATCH", "-dQUIET",
        "-sDEVICE=pdfwrite",
        f"-dJPEGQ={jpeg_q}",
        "-dColorImageDownsampleType=/Bicubic",
        f"-dColorImageResolution={dpi}",
        "-dGrayImageDownsampleType=/Bicubic",
        f"-dGrayImageResolution={dpi}",
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dDetectDuplicateImages=true",
        f"-sOutputFile={dst}",
        str(src),
    ]
    subprocess.run(args, check=True, capture_output=True, text=True)


def _write_chunks(reader, chunks, paths) -> list[int]:
    sizes = []
    for ch, p in zip(chunks, paths):
        if p.exists():
            p.unlink()
        w = PdfWriter()
        for idx in ch:
            w.add_page(reader.pages[idx])
        with open(p, "wb") as f:
            w.write(f)
        sizes.append(p.stat().st_size)
    return sizes


def split(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    parts: int = typer.Option(..., "--parts", "-n", min=1, help="Number of output parts"),
    max_size: str = typer.Option("4MB", "--max-size", "-m", help="Max size per part, e.g. 4MB, 500KB"),
    out_dir: Path = typer.Option(None, "--out-dir", "-d", help="Output directory"),
    prefix: str = typer.Option(None, "--prefix", "-p", help="Filename prefix (default: <input>_part)"),
) -> None:
    """Split a PDF into N parts of <= max-size with maximum quality."""
    require("gs")  # check upfront
    target = _parse_size(max_size)
    if out_dir is None:
        out_dir = file.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    if prefix is None:
        prefix = file.stem + "_part"

    work = file.parent / f".{file.stem}.splitting.pdf"
    paths = [out_dir / f"{prefix}{i+1:02d}.pdf" for i in range(parts)]
    # Clean up any pre-existing output files
    for p in paths:
        p.unlink(missing_ok=True)

    for q, dpi in QUALITY_LADDER:
        if work.exists():
            work.unlink()
        console.print(f"[dim]Trying q={q}, dpi={dpi}…[/dim]")
        _gs_repack(file, work, q, dpi)
        reader = PdfReader(str(work))
        total = len(reader.pages)
        base = total // parts
        rem = total - base * parts
        chunks = []
        i = 0
        for k in range(parts):
            extra = 1 if k < rem else 0
            chunks.append(list(range(i, i + base + extra)))
            i += base + extra
        sizes = _write_chunks(reader, chunks, paths)
        if all(s <= target for s in sizes):
            work.unlink(missing_ok=True)
            _report(chunks, paths, sizes, q, dpi)
            return

    work.unlink(missing_ok=True)
    raise RuntimeError(
        f"Could not split into {parts} parts of <= {fmt_bytes(target)} even at the lowest tested quality."
    )


def _report(chunks, paths, sizes, q, dpi):
    console.print(f"\n[green]Split successful (q={q}, dpi={dpi})[/green]")
    for ch, p, sz in zip(chunks, paths, sizes):
        console.print(f"  {p.name}: pages {ch[0]+1}-{ch[-1]+1}  {fmt_bytes(sz)}")


def _parse_size(s: str) -> int:
    s = s.strip().upper().replace(" ", "")
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    # Match longest suffix first
    for u in ("GB", "MB", "KB", "B"):
        if s.endswith(u):
            num = s[: -len(u)]
            return int(float(num) * units[u])
    return int(s)
