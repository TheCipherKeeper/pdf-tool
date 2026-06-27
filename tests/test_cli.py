"""Smoke tests for the CLI via Typer's CliRunner.

These exercise the command wiring + help output and a few end-to-end paths
that don't require external binaries (text via pypdf fallback, docx ops).
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from pdf_tool.cli import app

runner = CliRunner()


def test_version():
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "0.3.0" in res.stdout


def test_doctor_runs():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "External binaries" in res.stdout
    assert "Python libraries" in res.stdout


def test_help_lists_all_commands():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    for cmd in ("info", "merge", "rotate", "encrypt", "watermark", "docx2pdf", "pdf2docx", "docx"):
        assert cmd in res.stdout


def test_docx_subgroup_help():
    res = runner.invoke(app, ["docx", "--help"])
    assert res.exit_code == 0
    assert "info" in res.stdout
    assert "text" in res.stdout
    assert "merge" in res.stdout


def test_text_command_pypdf_fallback(pdf_with_text):
    """If poppler weren't available, text would fall back to pypdf. Either way it must run."""
    res = runner.invoke(app, ["text", str(pdf_with_text)])
    assert res.exit_code == 0, res.stdout
    assert "Page 1" in res.stdout


def test_text_command_discrete_pages(pdf_with_text):
    """Bug fix: discrete --pages 1,3 must yield pages 1 and 3, not 1-3."""
    res = runner.invoke(app, ["text", str(pdf_with_text), "-p", "1,3"])
    assert res.exit_code == 0, res.stdout
    assert "Page 1" in res.stdout
    assert "Page 3" in res.stdout
    assert "Page 2" not in res.stdout
    assert "Page 4" not in res.stdout


def test_docx_text_command(docx_basic):
    res = runner.invoke(app, ["docx", "text", str(docx_basic)])
    assert res.exit_code == 0, res.stdout
    assert "First paragraph" in res.stdout


def test_docx_info_command(docx_basic):
    res = runner.invoke(app, ["docx", "info", str(docx_basic)])
    assert res.exit_code == 0, res.stdout
    assert "Sample Title" in res.stdout


def test_missing_file_clean_error(tmp_path):
    res = runner.invoke(app, ["info", str(tmp_path / "nope.pdf")])
    assert res.exit_code != 0
    # Should be a clean BadParameter message, not a Python traceback
    assert "not found" in (res.stdout + (res.output or "")).lower()


def test_encrypt_decrypt_cli_roundtrip(tmp_pdf, tmp_path):
    enc = tmp_path / "enc.pdf"
    dec = tmp_path / "dec.pdf"
    r = runner.invoke(app, ["encrypt", str(tmp_pdf), "--user-pw", "s3cret", "-o", str(enc)])
    assert r.exit_code == 0, r.stdout
    r2 = runner.invoke(app, ["decrypt", str(enc), "-o", str(dec), "--password", "s3cret"])
    assert r2.exit_code == 0, r2.stdout


def test_is_scanned_command_text_pdf(pdf_with_text):
    res = runner.invoke(app, ["is-scanned", str(pdf_with_text)])
    assert res.exit_code == 0, res.stdout
    assert "has a text layer" in res.stdout


def test_is_scanned_command_scanned_pdf(scanned_pdf):
    res = runner.invoke(app, ["is-scanned", str(scanned_pdf)])
    assert res.exit_code == 0, res.stdout
    assert "SCANNED" in res.stdout


def test_text_ocr_fallback_cli(scanned_pdf):
    import pytest
    from pdf_tool.core.ocr import available_engines
    if not available_engines():
        pytest.skip("no OCR engine installed")
    res = runner.invoke(app, ["text", str(scanned_pdf), "--ocr-fallback", "--lang", "en", "--ocr-dpi", "200"])
    assert res.exit_code == 0, res.stdout
    up = res.stdout.upper()
    assert "HELLO" in up or "WORLD" in up


def test_ocr_engine_lang_parsing():
    from pdf_tool.core.ocr import parse_langs, tesseract_codes, easyocr_codes
    assert parse_langs("en,ru,ja") == ["en", "ru", "ja"]
    assert parse_langs("rus+eng") == ["ru", "en"]
    assert tesseract_codes(["en", "ru", "ja"]) == "eng+rus+jpn"
    assert easyocr_codes(["en", "ru", "ja"]) == ["en", "ru", "ja"]