"""Tests for the MS Word (docx) operations."""
from __future__ import annotations

from pathlib import Path

from docx import Document

from pdf_tool.core import docx as core


def test_docx_info(docx_basic):
    info = core.docx_info(docx_basic)
    assert info["paragraphs"] >= 2
    assert info["words"] > 0
    assert info["title"] == "Sample Title"
    assert info["author"] == "Tester"


def test_docx_text_includes_paragraphs_and_table(docx_basic):
    text = core.docx_text(docx_basic)
    assert "First paragraph" in text
    assert "Second paragraph" in text
    # Table cell content should be present
    assert "A1" in text and "B1" in text and "A2" in text and "B2" in text


def test_docx_merge(docx_basic, docx_second, tmp_path):
    out = tmp_path / "merged.docx"
    n = core.docx_merge([docx_basic, docx_second], out)
    assert n == 2
    doc = Document(str(out))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "First paragraph" in full_text
    assert "Appended paragraph from second doc." in full_text


def test_pdf2docx_without_libreoffice_graceful(pdf_with_text, tmp_path):
    """When soffice is missing, conversion raises a clear RuntimeError, not a crash."""
    import pytest
    from pdf_tool.backends import BIN
    if BIN.soffice is not None:
        pytest.skip("LibreOffice is installed on this box; skipping the missing-binary path.")
    with pytest.raises(RuntimeError, match="soffice"):
        core.libreoffice_convert(pdf_with_text, 'docx:"MS Word 2007 XML"', tmp_path / "x.docx")