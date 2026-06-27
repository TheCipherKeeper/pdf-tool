"""Command: pdf-tool compress <file>

Wraps ghostscript with sensible defaults and a target-size mode that
searches for the highest-quality settings that fit.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..backends import require
from ..utils import fmt_bytes, parse_size, safe_print

console = Console()

# Standard gs presets
PRESETS = {
    "prepress": "-dPDFSETTINGS=/prepress",   # lossless recompress
    "printer":  "-dPDFSETTINGS=/printer",    # 300 dpi JPEG q90
    "ebook":    "-dPDFSETTINGS=/ebook",      # 150 dpi JPEG q85
    "screen":   "-dPDFSETTINGS=/screen",     #  72 dpi JPEG q75
}

# Quality ladder for --target-size
QUALITY_LADDER = [
    (98, 300), (95, 300), (92, 300), (90, 300),
    (90, 250), (90, 200), (88, 200), (85, 200),
    (85, 180), (85, 160), (85, 150), (82, 150),
    (80, 150), (80, 140), (80, 130), (78, 130),
    (75, 120), (72, 110), (70, 100), (65, 90),
]


def _gs_with(extra: list[str], src: Path, dst: Path, password: Optional[str]) -> None:
    gs = require("gs")
    args = [
        str(gs),
        "-dNOPAUSE", "-dBATCH", "-dQUIET",
        "-sDEVICE=pdfwrite",
        f"-sOutputFile={dst}",
        *extra,
        str(src),
    ]
    if password is not None:
        # Insert the password flag before the input path.
        args.insert(-1, f"-dPDFPassword={password}")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ghostscript failed (exit {result.returncode}):\n{result.stderr or result.stdout}"
        )


def _report(before: Path, after: Path) -> None:
    b = before.stat().st_size
    a = after.stat().st_size
    delta = (a - b) / b * 100 if b else 0
    color = "green" if a < b else "yellow"
    arrow = "down" if a < b else "up"
    safe_print(console, f"[{color}]{arrow} {fmt_bytes(b)} -> {fmt_bytes(a)} ({delta:+.1f}%)[/{color}]  ->  {after}")


def compress(
    file: Path,
    out: Optional[Path] = None,
    preset: str = "ebook",
    target_size: Optional[str] = None,
    jpeg_q: Optional[int] = None,
    dpi: Optional[int] = None,
    password: Optional[str] = None,
) -> None:
    """Compress a PDF with ghostscript."""
    require("gs")
    if out is None:
        out = file.with_name(file.stem + ".compressed.pdf")

    # If --target-size is set, sweep the quality ladder
    if target_size:
        target = parse_size(target_size)
        ladder = QUALITY_LADDER
        # If user also passed jpeg_q/dpi, restrict to those
        if jpeg_q is not None or dpi is not None:
            console.print("[yellow]Ignoring --preset, using --jpeg-q/--dpi[/yellow]")
            ladder = [(jpeg_q or 90, dpi or 150)]
        for q, d in ladder:
            tmp = out.with_suffix(".tmp.pdf")
            extra = [
                f"-dJPEGQ={q}",
                "-dColorImageDownsampleType=/Bicubic",
                f"-dColorImageResolution={d}",
                "-dGrayImageDownsampleType=/Bicubic",
                f"-dGrayImageResolution={d}",
                "-dDownsampleColorImages=true",
                "-dDownsampleGrayImages=true",
                "-dDetectDuplicateImages=true",
            ]
            _gs_with(extra, file, tmp, password)
            size = tmp.stat().st_size
            ok = size <= target
            safe_print(console, f"  q={q:3d}, dpi={d:3d} -> {fmt_bytes(size)}  {'OK' if ok else 'over'}")
            if ok:
                shutil.move(tmp, out)
                _report(file, out)
                return
            tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Could not fit into {fmt_bytes(target)} even at the lowest tested quality.")

    # Preset mode (or custom q/dpi)
    if jpeg_q is not None or dpi is not None:
        if preset != "ebook":
            console.print("[yellow]Ignoring --preset, using --jpeg-q/--dpi[/yellow]")
        extra = []
        if jpeg_q is not None:
            extra.append(f"-dJPEGQ={jpeg_q}")
        if dpi is not None:
            extra += [
                "-dColorImageDownsampleType=/Bicubic",
                f"-dColorImageResolution={dpi}",
                "-dGrayImageDownsampleType=/Bicubic",
                f"-dGrayImageResolution={dpi}",
                "-dDownsampleColorImages=true",
                "-dDownsampleGrayImages=true",
            ]
    else:
        if preset not in PRESETS:
            raise typer.BadParameter(f"Unknown preset '{preset}'. Use: {', '.join(PRESETS)}")
        extra = [PRESETS[preset]]

    _gs_with(extra, file, out, password)
    _report(file, out)