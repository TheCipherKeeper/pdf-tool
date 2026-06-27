"""Tests for core PDF operations (rotate/extract/delete/encrypt/decrypt/rearrange)."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_tool.core import pdf as core
from pdf_tool.utils import parse_pages


def _pages(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def test_extract_subset(tmp_pdf, tmp_path):
    out = tmp_path / "out.pdf"
    n = core.extract(tmp_pdf, "1,3,5", out)
    assert n == 3
    assert _pages(out) == 3


def test_delete_pages(tmp_pdf, tmp_path):
    out = tmp_path / "out.pdf"
    removed = core.delete(tmp_pdf, "2,4", out)
    assert removed == 2
    # 5 pages - 2 removed = 3 kept
    assert _pages(out) == 3


def test_rearrange_roundtrip(tmp_pdf, tmp_path):
    from pdf_tool.commands.rearrange_cmd import rearrange
    out = tmp_path / "out.pdf"
    rearrange(tmp_pdf, "5,4,3,2,1", out)
    assert _pages(out) == 5


def test_encrypt_decrypt_roundtrip(tmp_pdf, tmp_path):
    enc = tmp_path / "enc.pdf"
    core.encrypt(tmp_pdf, enc, user_pw="secret")
    # Output must be encrypted
    r = PdfReader(str(enc))
    assert r.is_encrypted

    dec = tmp_path / "dec.pdf"
    core.decrypt(enc, dec, password="secret")
    r2 = PdfReader(str(dec))
    assert not r2.is_encrypted
    assert _pages(dec) == _pages(tmp_pdf)


def test_decrypt_wrong_password(tmp_pdf, tmp_path):
    enc = tmp_path / "enc.pdf"
    core.encrypt(tmp_pdf, enc, user_pw="secret")
    import pytest
    with pytest.raises(RuntimeError):
        core.decrypt(enc, tmp_path / "dec.pdf", password="wrong")


def test_open_encrypted_without_password_raises(tmp_pdf, tmp_path):
    import pytest
    enc = tmp_path / "enc.pdf"
    core.encrypt(tmp_pdf, enc, user_pw="secret")
    with pytest.raises(RuntimeError, match="encrypted"):
        # Reading an encrypted PDF without supplying a password must raise.
        core.extract(enc, "1", tmp_path / "x.pdf")


def test_metadata_set_and_strip(tmp_pdf, tmp_path):
    out = tmp_path / "meta.pdf"
    core.set_metadata(tmp_pdf, out, title="Hello", author="Me")
    r = PdfReader(str(out))
    assert r.metadata.get("/Title") == "Hello"
    assert r.metadata.get("/Author") == "Me"

    stripped = tmp_path / "stripped.pdf"
    core.set_metadata(out, stripped, strip=True)
    r2 = PdfReader(str(stripped))
    # Title should be gone
    assert not (r2.metadata or {}).get("/Title")


def test_watermark(tmp_pdf, tmp_path):
    n = core.watermark(tmp_pdf, tmp_path / "wm.pdf", "DRAFT")
    assert n == _pages(tmp_pdf)
    assert (tmp_path / "wm.pdf").exists()


def test_split_too_many_parts(tmp_pdf, tmp_path, capsys):
    """Bug fix: parts > pages must raise cleanly, not traceback."""
    import pytest
    import typer
    from pdf_tool.commands.split_cmd import split
    with pytest.raises(typer.BadParameter):
        split(tmp_pdf, parts=10, max_size="4MB", out_dir=tmp_path, prefix="p")


# ---------------------------------------------------------------------------
# Scan detection + OCR fallback
# ---------------------------------------------------------------------------

def test_is_scanned_text_pdf_not_scanned(pdf_with_text):
    from pdf_tool.core.pdf import is_scanned
    r = is_scanned(pdf_with_text)
    assert r["is_scanned"] is False
    assert r["scanned_pages"] == []


def test_is_scanned_scanned_pdf_detected(scanned_pdf):
    from pdf_tool.core.pdf import is_scanned
    r = is_scanned(scanned_pdf)
    assert r["is_scanned"] is True
    assert len(r["scanned_pages"]) == r["total"]


def test_text_plain_returns_empty_on_scanned(scanned_pdf):
    """Without --ocr-fallback, a scanned PDF yields (near) no text."""
    from pdf_tool.commands.text_cmd import text
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        text(scanned_pdf)
    # The image-only page has no extractable text layer.
    assert "OCR ME HELLO" not in buf.getvalue().upper()


def test_text_ocr_fallback_recovers_scanned_text(scanned_pdf):
    """--ocr-fallback runs tesseract on the scanned page and recovers text."""
    import pytest
    from pdf_tool.backends import BIN
    if BIN.tesseract is None:
        pytest.skip("tesseract not installed; OCR-fallback test requires it.")
    if "eng" not in BIN.tesseract_langs():
        pytest.skip("tesseract 'eng' language data not installed")
    from pdf_tool.commands.text_cmd import text
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        text(scanned_pdf, ocr_fallback=True, ocr_lang="eng", ocr_dpi=200)
    out = buf.getvalue().upper()
    # OCR must recover the actual rendered words (not just the stats line).
    assert "HELLO" in out or "WORLD" in out