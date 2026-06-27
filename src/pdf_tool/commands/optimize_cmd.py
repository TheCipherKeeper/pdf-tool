"""Command: pdf-tool optimize <file>"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from ..backends import require
from ..utils import fmt_bytes, safe_print

console = Console()


def optimize(
    file: Path,
    out: Path | None = None,
    linearize: bool = False,
    compress_streams: bool = True,
    object_streams: bool = True,
    remove_metadata: bool = False,
) -> None:
    """Lossless optimization via qpdf (smaller file, identical content)."""
    qpdf = require("qpdf")
    overwrite_input = out is None
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

    before = file.stat().st_size
    if overwrite_input or out == file:
        # qpdf refuses to write to the same path as the input. Write to a
        # temp file then atomically replace the input.
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", dir=file.parent, delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
        try:
            args += [str(file), str(tmp_path)]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                tmp_path.unlink(missing_ok=True)
                raise RuntimeError(f"qpdf failed: {result.stderr}")
            tmp_path.replace(file)
            target = file
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        args += [str(file), str(out)]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"qpdf failed: {result.stderr}")
        target = out

    after = target.stat().st_size
    delta = (after - before) / before * 100 if before else 0
    arrow = "down" if after < before else "up"
    color = "green" if after < before else "yellow"
    safe_print(
        console,
        f"[{color}]{arrow} {fmt_bytes(before)} -> {fmt_bytes(after)} "
        f"({delta:+.1f}%)[/{color}]  ->  {target}"
    )