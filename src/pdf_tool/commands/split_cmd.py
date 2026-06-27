"""Command: pdf-tool split <file> --parts N --max-size 4MB

Splits a PDF into N parts, each <= max-size, picking the highest
ghostscript quality that fits.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from pypdf import PdfReader, PdfWriter

from ..backends import require
from ..utils import fmt_bytes, parse_size

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
    import subprocess

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ghostscript failed (exit {result.returncode}):\n{result.stderr or result.stdout}"
        )


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
    file: Path,
    parts: int,
    max_size: str = "4MB",
    out_dir: Optional[Path] = None,
    prefix: Optional[str] = None,
) -> None:
    """Split a PDF into N parts of <= max-size with maximum quality."""
    require("gs")  # check upfront
    if parts < 1:
        raise typer.BadParameter("--parts must be >= 1.")
    target = parse_size(max_size)
    if out_dir is None:
        out_dir = file.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    if prefix is None:
        prefix = file.stem + "_part"

    # Pre-check page count so parts > pages fails cleanly up front.
    pre_reader = PdfReader(str(file))
    total_pages = len(pre_reader.pages)
    if parts > total_pages:
        raise typer.BadParameter(
            f"Cannot split {total_pages}-page PDF into {parts} parts "
            f"(parts must be <= page count)."
        )
    del pre_reader

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
        if ch:
            console.print(f"  {p.name}: pages {ch[0]+1}-{ch[-1]+1}  {fmt_bytes(sz)}")
        else:
            console.print(f"  {p.name}: (empty)  {fmt_bytes(sz)}")