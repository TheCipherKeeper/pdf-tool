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


# ---------------------------------------------------------------------------
# Scan detection + OCR text fallback (machine vision via tesseract)
# ---------------------------------------------------------------------------

def _open_fitz(path: Path, password: Optional[str] = None):
    """Open a PDF with PyMuPDF, authenticating if encrypted."""
    import fitz

    doc = fitz.open(str(path))
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            doc.close()
            raise RuntimeError(
                f"Cannot open {path}: encrypted, wrong or missing password."
            )
    return doc


def is_scanned(path: Path, password: Optional[str] = None, threshold: int = 10) -> dict:
    """Detect image-only ("scanned") pages that have no real text layer.

    A page is flagged as scanned when its extracted text is shorter than
    `threshold` characters AND it contains at least one image. Returns a dict:
    {total, scanned_pages: [1-based], is_scanned: bool (majority of pages)}.
    """
    doc = _open_fitz(path, password)
    scanned: list[int] = []
    total = len(doc)
    for i, page in enumerate(doc, start=1):
        text_len = len(page.get_text("text").strip())
        has_image = len(page.get_images()) > 0
        if text_len < threshold and has_image:
            scanned.append(i)
    doc.close()
    is_scan = bool(scanned) and len(scanned) * 2 >= total  # majority of pages
    return {"total": total, "scanned_pages": scanned, "is_scanned": is_scan}


def text_with_ocr_fallback(
    path: Path,
    selected: Optional[list[int]],
    *,
    lang: str = "rus+eng",
    dpi: int = 300,
    threshold: int = 10,
    password: Optional[str] = None,
) -> tuple[list[str], dict]:
    """Per-page text with automatic OCR on image-only pages.

    For each selected page: take the text layer (via PyMuPDF); if it is shorter
    than `threshold` chars and the page has an image, render it to an image and
    run tesseract to recover text. Returns (per_page_text, stats) where stats
    tracks ocr_pages, skipped (no tesseract), and blank pages.
    """
    import os
    import subprocess
    import tempfile

    import fitz

    from ..backends import BIN

    doc = _open_fitz(path, password)
    total = len(doc)
    if selected is None:
        selected = list(range(1, total + 1))

    has_tesseract = BIN.tesseract is not None
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    pages_text: list[str] = []
    stats = {"ocr_pages": 0, "skipped_no_tesseract": 0, "blank_pages": 0,
             "tesseract_errors": 0}

    for n in selected:
        page = doc[n - 1]
        text = page.get_text("text")
        stripped = text.strip()
        has_image = len(page.get_images()) > 0

        if len(stripped) < threshold and has_image:
            if has_tesseract:
                ocr_text, ok = _ocr_page_to_text(page, matrix, lang, BIN.tesseract)
                pages_text.append(ocr_text)
                stats["ocr_pages"] += 1
                if not ok:
                    stats["tesseract_errors"] += 1
            else:
                pages_text.append("")
                stats["skipped_no_tesseract"] += 1
        elif len(stripped) < threshold:
            # No text and no image -> genuinely blank page.
            pages_text.append("")
            stats["blank_pages"] += 1
        else:
            pages_text.append(text)

    doc.close()
    return pages_text, stats


def _ocr_page_to_text(page, matrix, lang: str, tesseract) -> tuple[str, bool]:
    """Render a page to PNG and run tesseract to get plain text.

    Returns (text, ok). ok=False signals tesseract itself failed (e.g. missing
    language data) so callers can warn the user instead of silently emitting
    empty text.
    """
    import os
    import subprocess
    import tempfile
    from pathlib import Path

    pix = page.get_pixmap(matrix=matrix)
    fd, img_name = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    fd2, base_name = tempfile.mkstemp()
    os.close(fd2)
    txt_path = Path(base_name + ".txt")
    try:
        pix.save(img_name)
        result = subprocess.run(
            [str(tesseract), img_name, base_name, "-l", lang, "txt"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return "", False
        if txt_path.exists():
            return txt_path.read_text(encoding="utf-8", errors="replace"), True
        return "", True
    finally:
        for p in (img_name, str(txt_path)):
            try:
                os.unlink(p)
            except OSError:
                pass