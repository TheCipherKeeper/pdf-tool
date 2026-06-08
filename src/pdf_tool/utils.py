"""Shared helpers: file-size formatting, page iteration, etc."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .backends import BIN, require


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


_UNICODE_REPLACEMENTS = {
    "↓": "down", "↑": "up", "→": "->",
    "←": "<-", "✓": "OK", "✗": "X",
    "•": "*", "·": ".",
}


def safe_print(console, text: str) -> None:
    """Print text, falling back to ASCII on Windows console encoding issues."""
    try:
        console.print(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        safe = text
        for k, v in _UNICODE_REPLACEMENTS.items():
            safe = safe.replace(k, v)
        import sys
        # Strip rich markup markers if any
        import re
        safe = re.sub(r"\[/?[a-z][^\]]*\]", "", safe)
        sys.stdout.write(safe + "\n")


def need_pages_count(pdf: Path) -> int:
    """Return the page count of a PDF (pypdf fallback if pdfinfo missing)."""
    if BIN.pdfinfo:
        out = subprocess.run(
            [str(BIN.pdfinfo), str(pdf)], capture_output=True, text=True, check=True
        ).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    from pypdf import PdfReader
    return len(PdfReader(str(pdf)).pages)
