"""Command: pdf-tool optimize <file>"""
from pathlib import Path

import typer
from rich.console import Console

from ..backends import BIN, require
from ..utils import fmt_bytes, safe_print

console = Console()


def optimize(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(None, "--out", "-o", help="Output file (default: overwrite input)"),
    linearize: bool = typer.Option(False, "--linearize", "-L", help="Optimize for web (fast web view)"),
    compress_streams: bool = typer.Option(True, "--compress-streams/--no-compress-streams"),
    object_streams: bool = typer.Option(True, "--object-streams/--no-object-streams"),
    remove_metadata: bool = typer.Option(False, "--remove-metadata", help="Strip XMP metadata"),
) -> None:
    """Lossless optimization via qpdf (smaller file, identical content)."""
    qpdf = require("qpdf")
    if out is None:
        out = file

    args = [str(qpdf)]
    if linearize:
        args.append("--linearize")
    if compress_streams:
        args.append("--compress-streams=y")
    if object_streams:
        args.append("--object-streams=generate")
    if remove_metadata:
        args.append("--remove-metadata")
    args += [str(file), str(out)]

    before = file.stat().st_size
    import subprocess
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"qpdf failed: {result.stderr}")
    after = out.stat().st_size

    delta = (after - before) / before * 100
    arrow = "down" if after < before else "up"
    color = "green" if after < before else "yellow"
    safe_print(
        console,
        f"[{color}]{arrow} {fmt_bytes(before)} -> {fmt_bytes(after)} "
        f"({delta:+.1f}%)[/{color}]  ->  {out}"
    )
