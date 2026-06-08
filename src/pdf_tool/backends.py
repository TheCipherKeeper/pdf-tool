"""Locate external binaries (gs, qpdf, tesseract, poppler) and wrap calls.

We don't hard-code paths; we search a set of likely install locations and
PATH. If a binary isn't found, we raise a clear error so the user knows
what to install.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BinPaths:
    gs: Optional[Path] = None
    qpdf: Optional[Path] = None
    tesseract: Optional[Path] = None
    pdftotext: Optional[Path] = None
    pdfinfo: Optional[Path] = None
    mutool: Optional[Path] = None

    def report(self) -> str:
        lines = ["External binaries:"]
        for name in ("gs", "qpdf", "tesseract", "pdftotext", "pdfinfo", "mutool"):
            p = getattr(self, name)
            lines.append(f"  {name:<11} {'OK ' if p else 'MISSING'}  {p or '(install and add to PATH)'}")
        return "\n".join(lines)


# Common install locations on Windows. Order matters: more specific first.
_WINDOWS_CANDIDATES = {
    "gs": [
        r"C:\Program Files\gs\gs*\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs*\bin\gswin32c.exe",
        r"C:\Program Files\PDF24\gs\bin\gswin64c.exe",
    ],
    "qpdf": [
        r"C:\Program Files\qpdf\bin\qpdf.exe",
        r"C:\Program Files\PDF24\qpdf\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf\bin\qpdf.exe",
    ],
    "tesseract": [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\PDF24\tesseract\tesseract.exe",
    ],
    "pdftotext": [
        r"C:\Program Files\poppler\Library\bin\pdftotext.exe",
        r"C:\Program Files\poppler\bin\pdftotext.exe",
        r"C:\Program Files (x86)\poppler\bin\pdftotext.exe",
    ],
    "pdfinfo": [
        r"C:\Program Files\poppler\Library\bin\pdfinfo.exe",
        r"C:\Program Files\PDF24\poppler\bin\pdfinfo.exe",
        r"C:\Program Files\poppler\bin\pdfinfo.exe",
    ],
    "mutool": [
        r"C:\Program Files\MuTools\mutool.exe",
        r"C:\Program Files\mupdf-tools\mutool.exe",
    ],
}


def _find_windows(name: str) -> Optional[Path]:
    import glob
    for pattern in _WINDOWS_CANDIDATES.get(name, []):
        for match in glob.glob(pattern):
            if Path(match).exists():
                return Path(match)
    return None


def find_binaries() -> BinPaths:
    paths = BinPaths()
    # First try PATH
    for name in ("gs", "qpdf", "tesseract", "pdftotext", "pdfinfo", "mutool"):
        exe = shutil.which(name)
        if exe:
            setattr(paths, name, Path(exe))
    # Fall back to Windows-specific searches
    if os.name == "nt":
        for name in ("gs", "qpdf", "tesseract", "pdftotext", "pdfinfo", "mutool"):
            if getattr(paths, name) is None:
                found = _find_windows(name)
                if found:
                    setattr(paths, name, found)
    return paths


BIN = find_binaries()


def run(cmd: list[Path | str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess, surfacing stderr on failure."""
    result = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kwargs)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(map(str, cmd))}\n"
            f"STDERR:\n{result.stderr}"
        )
    return result


def require(name: str) -> Path:
    """Get a binary's path or raise with a helpful message."""
    p = getattr(BIN, name)
    if p is None:
        raise RuntimeError(
            f"Required binary '{name}' not found. Install it and ensure it's on PATH.\n"
            f"Current status:\n{BIN.report()}"
        )
    return p
