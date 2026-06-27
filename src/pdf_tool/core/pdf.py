"""Shared PDF operations built on pypdf / pikepdf / PyMuPDF.

Kept dependency-light: pypdf for structural ops, pikepdf for repair,
PyMuPDF (fitz) for rendering-based ops (watermark).
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter, PasswordType
from pypdf.errors import PdfReadError

from ..utils import parse_pages


def open_reader(path: Path, password: Optional[str] = None) -> PdfReader:
    """Open a PDF for reading, decrypting with an optional password.

    Raises a clear RuntimeError if the password is wrong/missing.
    """
    try:
        reader = PdfReader(str(path))
    except PdfReadError as e:
        raise RuntimeError(f"Could not read PDF {path}: {e}") from e
    if reader.is_encrypted:
        if password is None:
            raise RuntimeError(
                f"PDF is encrypted. Provide a password with --password.\n  {path}"
            )
        if not reader.decrypt(password):
            raise RuntimeError(f"Wrong password for {path}.")
    return reader


def write_pdf(writer: PdfWriter, out: Path) -> None:
    """Write a PdfWriter to a path, creating parent dirs as needed."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)


def rotate(path: Path, angle: int, pages: Optional[str], out: Path, password: Optional[str] = None) -> int:
    """Rotate selected pages (or all) by `angle` degrees. Returns count rotated."""
    if angle not in (90, 180, 270):
        raise ValueError("angle must be 90, 180, or 270")
    reader = open_reader(path, password)
    total = len(reader.pages)
    targets = set(parse_pages(pages, total)) if pages else set(range(1, total + 1))

    writer = PdfWriter()
    for i, page in enumerate(reader.pages, start=1):
        if i in targets:
            page.rotate(angle)
        writer.add_page(page)
    write_pdf(writer, out)
    return len(targets)


def extract(path: Path, pages: str, out: Path, password: Optional[str] = None) -> int:
    """Extract the given page subset into a new PDF. Returns page count."""
    reader = open_reader(path, password)
    total = len(reader.pages)
    nums = parse_pages(pages, total)
    writer = PdfWriter()
    for n in nums:
        writer.add_page(reader.pages[n - 1])
    write_pdf(writer, out)
    return len(nums)


def delete(path: Path, pages: str, out: Path, password: Optional[str] = None) -> int:
    """Remove the given pages. Returns count removed."""
    reader = open_reader(path, password)
    total = len(reader.pages)
    remove = set(parse_pages(pages, total))
    writer = PdfWriter()
    kept = 0
    for i, page in enumerate(reader.pages, start=1):
        if i in remove:
            continue
        writer.add_page(page)
        kept += 1
    write_pdf(writer, out)
    return len(remove)


def encrypt(
    path: Path,
    out: Path,
    user_pw: str,
    owner_pw: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Apply encryption with a user (and optional owner) password.

    Uses AES-256 when the optional `cryptography` package is available; falls
    back to 128-bit RC4 (no extra deps) otherwise.
    """
    reader = open_reader(path, password)
    writer = PdfWriter(clone_from=reader)
    kwargs = dict(
        user_password=user_pw,
        owner_password=owner_pw if owner_pw is not None else user_pw,
    )
    try:
        writer.encrypt(algorithm="AES-256", **kwargs)
    except Exception:
        # cryptography package missing -> fall back to 128-bit (no extra dep).
        writer.encrypt(use_128bit=True, **kwargs)
    write_pdf(writer, out)


def decrypt(path: Path, out: Path, password: str) -> None:
    """Remove encryption from a PDF (requires the user/owner password)."""
    reader = open_reader(path, password)
    writer = PdfWriter(clone_from=reader)
    write_pdf(writer, out)


def set_metadata(
    path: Path,
    out: Path,
    *,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
    strip: bool = False,
    password: Optional[str] = None,
) -> dict:
    """Set (or strip) document metadata. Returns the applied metadata dict."""
    reader = open_reader(path, password)
    writer = PdfWriter(clone_from=reader)
    if strip:
        # Replace the Info dictionary with an empty one (add_metadata only
        # merges, so it cannot strip existing keys).
        from pypdf.generic import DictionaryObject
        writer._info = writer._add_object(DictionaryObject())
    else:
        meta = dict(reader.metadata or {})
        if title is not None:
            meta["/Title"] = title
        if author is not None:
            meta["/Author"] = author
        if subject is not None:
            meta["/Subject"] = subject
        if keywords is not None:
            meta["/Keywords"] = keywords
        writer.add_metadata(meta)
    write_pdf(writer, out)
    return dict(writer.metadata or {}) if not strip else {}


def watermark(path: Path, out: Path, text: str, *, fontsize: int = 48, password: Optional[str] = None, color=(0.8, 0.8, 0.8), angle: float = -45) -> int:
    """Stamp a diagonal text watermark on every page via PyMuPDF. Returns page count.

    Uses a TextWriter with a morph (rotation) so arbitrary angles are supported
    (page.insert_text only accepts multiples of 90°).
    """
    import fitz  # PyMuPDF

    reader = open_reader(path, password)
    # Re-encode to a decrypted in-memory PDF so fitz can open it.
    tmp_bytes = io.BytesIO()
    w = PdfWriter(clone_from=reader)
    w.write(tmp_bytes)
    tmp_bytes.seek(0)

    doc = fitz.open(stream=tmp_bytes, filetype="pdf")
    font = fitz.Font("helv")
    n = len(doc)
    for page in doc:
        rect = page.rect
        tw = fitz.TextWriter(rect)
        text_width = font.text_length(text, fontsize=fontsize)
        text_height = fontsize
        pos = fitz.Point((rect.width - text_width) / 2, (rect.height + text_height) / 2)
        tw.append(pos, text, font=font, fontsize=fontsize)
        center = fitz.Point(rect.width / 2, rect.height / 2)
        morph = (center, fitz.Matrix(1, 1).prerotate(angle))
        tw.write_text(page, color=color, morph=morph, overlay=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    doc.close()
    return n


def repair(path: Path, out: Path) -> None:
    """Recover a damaged PDF using pikepdf (with qpdf as a stronger fallback)."""
    import pikepdf

    try:
        pdf = pikepdf.open(str(path), attempt_recovery=True)
        pdf.save(str(out))
        pdf.close()
    except Exception:
        # Stronger fallback: let qpdf reconstruct the xref.
        from ..backends import require, run as backend_run
        try:
            qpdf = require("qpdf")
            backend_run([qpdf, "--repair", str(path), "--", str(out)])
        except Exception as e:
            raise RuntimeError(f"Could not repair {path}: {e}") from e


def page_count(path: Path, password: Optional[str] = None) -> int:
    """Return the number of pages in a PDF."""
    reader = open_reader(path, password)
    return len(reader.pages)