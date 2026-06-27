"""Command: pdf-tool encrypt <file> --user-pw X [--owner-pw Y] -o out.pdf"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..core import pdf as core
from ..utils import safe_print

console = Console()


def encrypt(
    file: Path,
    user_pw: str,
    out: Optional[Path] = None,
    owner_pw: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Apply 256-bit AES encryption with a user (and optional owner) password."""
    if out is None:
        out = file.with_name(file.stem + ".encrypted.pdf")
    core.encrypt(file, out, user_pw, owner_pw, password)
    safe_print(console, f"[green]Encrypted[/green]  ->  {out}")