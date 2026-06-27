"""Locate external binaries (gs, qpdf, tesseract, poppler, libreoffice) and wrap calls.

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
    soffice: Optional[Path] = None

    @property
    def names(self) -> tuple[str, ...]:
        return ("gs", "qpdf", "tesseract", "pdftotext", "pdfinfo", "soffice")

    def tesseract_langs(self) -> list[str]:
        """Return the language codes tesseract can actually load, or []."""
        if self.tesseract is None:
            return []
        try:
            out = subprocess.run(
                [str(self.tesseract), "--list-langs"],
                capture_output=True, text=True,
            ).stdout
        except Exception:
            return []
        langs: list[str] = []
        for line in out.splitlines()[1:]:  # skip the "List of available..." header
            code = line.strip()
            if code:
                langs.append(code)
        return langs

    def report(self) -> str:
        lines = ["[bold]External binaries:[/bold]"]
        for name in self.names:
            p = getattr(self, name)
            state = "[green]OK[/green]" if p else "[red]MISSING[/red]"
            lines.append(f"  {name:<11} {state}  {p or '(install and add to PATH)'}")

        # Tesseract language data (OCR is unusable without it)
        if self.tesseract is not None:
            langs = self.tesseract_langs()
            if langs:
                lines.append(f"  tesseract langs: {', '.join(langs)}")
            else:
                lines.append(
                    "  [yellow]tesseract has NO language data — OCR (`ocr`, "
                    "`text --ocr-fallback`) cannot recognize text. Set "
                    "TESSDATA_PREFIX or install language packs.[/yellow]"
                )

        # Python library availability (some are optional / feature-gated)
        libs = _python_libs()
        lines.append("\n[bold]Python libraries:[/bold]")
        for name, ok in libs.items():
            state = "[green]OK[/green]" if ok else "[red]MISSING[/red]"
            lines.append(f"  {name:<11} {state}")

        if self.soffice is None:
            lines.append(
                "\n[yellow]LibreOffice (soffice) not found — "
                "`docx2pdf` and `pdf2docx` conversions are unavailable.[/yellow]"
            )
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
        r"C:\Program Files\PDF24\poppler\bin\pdftotext.exe",
    ],
    "pdfinfo": [
        r"C:\Program Files\poppler\Library\bin\pdfinfo.exe",
        r"C:\Program Files\PDF24\poppler\bin\pdfinfo.exe",
        r"C:\Program Files\poppler\bin\pdfinfo.exe",
    ],
    # LibreOffice: prefer soffice.com on Windows (returns after completion)
    "soffice": [
        r"C:\Program Files\LibreOffice\program\soffice.com",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
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
    for name in paths.names:
        exe = shutil.which(name)
        if exe:
            setattr(paths, name, Path(exe))
    # Fall back to Windows-specific searches
    if os.name == "nt":
        for name in paths.names:
            if getattr(paths, name) is None:
                found = _find_windows(name)
                if found:
                    setattr(paths, name, found)
    return paths


def _python_libs() -> dict[str, bool]:
    """Probe for optional/required Python libraries."""
    probes = {
        "PyMuPDF": "fitz",
        "pypdf": "pypdf",
        "pikepdf": "pikepdf",
        "Pillow": "PIL",
        "python-docx": "docx",
        "cryptography": "cryptography",
    }
    out: dict[str, bool] = {}
    for label, mod in probes.items():
        try:
            __import__(mod)
            out[label] = True
        except Exception:
            out[label] = False
    return out


BIN = find_binaries()


def require(name: str) -> Path:
    """Get a binary's path or raise with a helpful message."""
    p = getattr(BIN, name)
    if p is None:
        raise RuntimeError(
            f"Required binary '{name}' not found. Install it and ensure it's on PATH.\n"
            f"Current status:\n{BIN.report()}"
        )
    return p


def run(cmd: list[Path | str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess, surfacing stderr on failure."""
    result = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kwargs)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(map(str, cmd))}\n"
            f"STDERR:\n{result.stderr}"
        )
    return result