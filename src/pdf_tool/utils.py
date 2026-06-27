"""Shared helpers: file-size formatting, page-range parsing, file validation."""
from __future__ import annotations

import re
from pathlib import Path

import typer

_UNICODE_REPLACEMENTS = {
    "↓": "down", "↑": "up", "→": "->",
    "←": "<-", "✓": "OK", "✗": "X",
    "•": "*", "·": ".",
}


def fmt_bytes(n: int) -> str:
    """Human-readable byte size."""
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(f) < 1024:
            return f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} TB"


def safe_print(console, text: str) -> None:
    """Print text, falling back to ASCII on Windows console encoding issues."""
    try:
        console.print(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        import sys

        safe = text
        for k, v in _UNICODE_REPLACEMENTS.items():
            safe = safe.replace(k, v)
        # Strip rich markup markers if any
        safe = re.sub(r"\[/?[a-z][^\]]*\]", "", safe)
        sys.stdout.write(safe + "\n")


def parse_size(s: str) -> int:
    """Parse '4MB', '500KB', '1GB', or a bare byte count into an int."""
    s = s.strip().upper().replace(" ", "")
    units = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}
    for u in ("GB", "MB", "KB", "B"):
        if s.endswith(u):
            num = s[: -len(u)]
            return int(float(num) * units[u])
    return int(s)


def parse_pages(spec: str, total: int, *, allow_empty: bool = False) -> list[int]:
    """Parse a page spec like '1,3-5,8' into 1-based page numbers within 1..total.

    Validates strictly: out-of-range or malformed tokens raise ValueError.
    Duplicate / out-of-order pages are preserved (rearrange semantics).
    Returns a 1-based list. Raises ValueError if the result is empty (unless allow_empty).
    """
    out: list[int] = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            try:
                a, b = int(a), int(b)
            except ValueError:
                raise ValueError(f"Bad page range: {token!r}")
            if a > b:
                a, b = b, a
            for p in range(a, b + 1):
                if not (1 <= p <= total):
                    raise ValueError(f"Page {p} out of range (1..{total})")
                out.append(p)
        else:
            try:
                p = int(token)
            except ValueError:
                raise ValueError(f"Bad page number: {token!r}")
            if not (1 <= p <= total):
                raise ValueError(f"Page {p} out of range (1..{total})")
            out.append(p)
    if not out and not allow_empty:
        raise ValueError("No pages selected")
    return out


def require_file(p: Path, *, must_exist: bool = True) -> Path:
    """Validate that a path exists and is a readable file, with a clean error."""
    if must_exist and not p.exists():
        raise typer.BadParameter(f"File not found: {p}")
    if p.exists() and not p.is_file():
        raise typer.BadParameter(f"Not a file: {p}")
    return p