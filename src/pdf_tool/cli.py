"""pdf-tool: a Swiss-army CLI for PDF and MS Word manipulation."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .backends import BIN
from .utils import require_file

app = typer.Typer(
    name="pdf-tool",
    help="Swiss-army CLI for PDF and MS Word: split, merge, compress, OCR, convert, and more.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)
docx_app = typer.Typer(
    name="docx",
    help="MS Word (.docx) operations.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)
app.add_typer(docx_app, name="docx")

console = Console()


def _path(s: str) -> Path:
    return Path(s).expanduser().resolve()


def _file(s: str) -> Path:
    """Resolve and validate an input file path."""
    return require_file(_path(s))


# ---------------------------------------------------------------------------
# PDF commands
# ---------------------------------------------------------------------------

@app.command("info")
def info_cmd_run(file: str, fonts: bool = False, password: Optional[str] = None):
    """Show metadata and structure of a PDF."""
    from .commands import info_cmd
    info_cmd.info(_file(file), show_fonts=fonts, password=password)


@app.command("images")
def images_cmd_run(
    file: str,
    extract: bool = typer.Option(False, "--extract", "-e"),
    out: str = typer.Option("images", "--out", "-o"),
    min_size: int = typer.Option(0, "--min-size"),
):
    """List or extract all images in a PDF."""
    from .commands import images_cmd
    images_cmd.images(_file(file), extract=extract, out_dir=_path(out), min_size=min_size)


@app.command("text")
def text_cmd_run(
    file: str,
    layout: bool = typer.Option(False, "--layout", "-l"),
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    pages: Optional[str] = typer.Option(None, "--pages", "-p"),
    password: Optional[str] = None,
    ocr_fallback: bool = typer.Option(False, "--ocr-fallback", "-O", help="Auto-OCR scanned (image-only) pages via tesseract"),
    ocr_lang: str = typer.Option("rus+eng", "--ocr-lang", help="Tesseract language(s) for --ocr-fallback"),
    ocr_dpi: int = typer.Option(300, "--ocr-dpi", help="Render DPI for OCR in --ocr-fallback"),
    ocr_threshold: int = typer.Option(10, "--ocr-threshold", help="Min chars for a page to count as 'has text'"),
):
    """Extract text from a PDF. With --ocr-fallback, scanned pages are OCR'd."""
    from .commands import text_cmd
    text_cmd.text(
        _file(file),
        layout=layout,
        out=_path(out) if out else None,
        pages=pages,
        password=password,
        ocr_fallback=ocr_fallback,
        ocr_lang=ocr_lang,
        ocr_dpi=ocr_dpi,
        ocr_threshold=ocr_threshold,
    )


@app.command("optimize")
def optimize_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    linearize: bool = typer.Option(False, "--linearize", "-L"),
    compress_streams: bool = True,
    object_streams: bool = True,
    remove_metadata: bool = False,
):
    """Lossless optimization via qpdf."""
    from .commands import optimize_cmd
    optimize_cmd.optimize(
        _file(file),
        out=_path(out) if out else None,
        linearize=linearize,
        compress_streams=compress_streams,
        object_streams=object_streams,
        remove_metadata=remove_metadata,
    )


@app.command("compress")
def compress_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    preset: str = typer.Option("ebook", "--preset", "-p"),
    target_size: Optional[str] = typer.Option(None, "--target-size"),
    jpeg_q: Optional[int] = typer.Option(None, "--jpeg-q"),
    dpi: Optional[int] = typer.Option(None, "--dpi"),
    password: Optional[str] = None,
):
    """Compress a PDF with ghostscript."""
    from .commands import compress_cmd
    compress_cmd.compress(
        _file(file),
        out=_path(out) if out else None,
        preset=preset,
        target_size=target_size,
        jpeg_q=jpeg_q,
        dpi=dpi,
        password=password,
    )


@app.command("split")
def split_cmd_run(
    file: str,
    parts: int = typer.Option(..., "--parts", "-n", min=1),
    max_size: str = typer.Option("4MB", "--max-size", "-m"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", "-d"),
    prefix: Optional[str] = typer.Option(None, "--prefix", "-p"),
):
    """Split a PDF into N parts of <= max-size (auto-pick best quality)."""
    from .commands import split_cmd
    split_cmd.split(
        _file(file),
        parts=parts,
        max_size=max_size,
        out_dir=_path(out_dir) if out_dir else None,
        prefix=prefix,
    )


@app.command("merge")
def merge_cmd_run(
    files: list[str],
    out: str = typer.Option(..., "--out", "-o"),
    bookmarks: bool = True,
    password: Optional[str] = None,
):
    """Merge multiple PDFs into one."""
    from .commands import merge_cmd
    merge_cmd.merge([_file(f) for f in files], out=_path(out), bookmarks=bookmarks, password=password)


@app.command("rearrange")
def rearrange_cmd_run(
    file: str,
    pages: str = typer.Option(..., "--pages", "-p"),
    out: str = typer.Option(..., "--out", "-o"),
    password: Optional[str] = None,
):
    """Reorder/remove/duplicate pages in a PDF."""
    from .commands import rearrange_cmd
    rearrange_cmd.rearrange(_file(file), pages=pages, out=_path(out), password=password)


@app.command("preview")
def preview_cmd_run(
    file: str,
    out_dir: str = typer.Option("previews", "--out", "-o"),
    pages: Optional[str] = typer.Option(None, "--pages", "-p"),
    dpi: int = 150,
    fmt: str = typer.Option("png", "--format", "-f"),
):
    """Render pages of a PDF to PNG/JPEG images."""
    from .commands import preview_cmd
    preview_cmd.preview(_file(file), out_dir=_path(out_dir), pages=pages, dpi=dpi, fmt=fmt)


@app.command("ocr")
def ocr_cmd_run(
    file: str,
    out: str = typer.Option(..., "--out", "-o"),
    lang: str = typer.Option("rus+eng", "--lang", "-l"),
    dpi: int = 300,
    pages: Optional[str] = typer.Option(None, "--pages", "-p"),
):
    """OCR a scanned PDF (tesseract) into a searchable PDF."""
    from .commands import ocr_cmd
    ocr_cmd.ocr(_file(file), out=_path(out), lang=lang, dpi=dpi, pages=pages)


@app.command("rotate")
def rotate_cmd_run(
    file: str,
    angle: int = typer.Option(90, "--angle", "-a"),
    pages: Optional[str] = typer.Option(None, "--pages", "-p"),
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    password: Optional[str] = None,
):
    """Rotate pages (90/180/270) of a PDF."""
    from .commands import rotate_cmd
    rotate_cmd.rotate(_file(file), angle=angle, pages=pages, out=_path(out) if out else None, password=password)


@app.command("extract")
def extract_cmd_run(
    file: str,
    pages: str = typer.Option(..., "--pages", "-p"),
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    password: Optional[str] = None,
):
    """Extract a page range into a new PDF."""
    from .commands import extract_cmd
    extract_cmd.extract(_file(file), pages=pages, out=_path(out) if out else None, password=password)


@app.command("delete")
def delete_cmd_run(
    file: str,
    pages: str = typer.Option(..., "--pages", "-p"),
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    password: Optional[str] = None,
):
    """Remove pages from a PDF."""
    from .commands import delete_cmd
    delete_cmd.delete(_file(file), pages=pages, out=_path(out) if out else None, password=password)


@app.command("encrypt")
def encrypt_cmd_run(
    file: str,
    user_pw: str = typer.Option(..., "--user-pw"),
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    owner_pw: Optional[str] = typer.Option(None, "--owner-pw"),
    password: Optional[str] = None,
):
    """Apply 256-bit AES encryption to a PDF."""
    from .commands import encrypt_cmd
    encrypt_cmd.encrypt(_file(file), user_pw=user_pw, out=_path(out) if out else None, owner_pw=owner_pw, password=password)


@app.command("decrypt")
def decrypt_cmd_run(
    file: str,
    out: str = typer.Option(..., "--out", "-o"),
    password: str = typer.Option(..., "--password"),
):
    """Remove encryption from a PDF."""
    from .commands import decrypt_cmd
    decrypt_cmd.decrypt(_file(file), out=_path(out), password=password)


@app.command("metadata")
def metadata_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
    strip: bool = typer.Option(False, "--strip"),
    password: Optional[str] = None,
):
    """Set or strip PDF metadata."""
    from .commands import metadata_cmd
    metadata_cmd.metadata(
        _file(file),
        out=_path(out) if out else None,
        title=title, author=author, subject=subject, keywords=keywords,
        strip=strip, password=password,
    )


@app.command("watermark")
def watermark_cmd_run(
    file: str,
    text: str = typer.Option(..., "--text"),
    out: Optional[str] = typer.Option(None, "--out", "-o"),
    fontsize: int = typer.Option(48, "--fontsize"),
    password: Optional[str] = None,
):
    """Stamp a diagonal text watermark on every page."""
    from .commands import watermark_cmd
    watermark_cmd.watermark(_file(file), text=text, out=_path(out) if out else None, fontsize=fontsize, password=password)


@app.command("repair")
def repair_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
):
    """Recover a damaged PDF."""
    from .commands import repair_cmd
    repair_cmd.repair(_file(file), out=_path(out) if out else None)


@app.command("is-scanned")
def is_scanned_cmd_run(
    file: str,
    threshold: int = typer.Option(10, "--threshold", help="Min chars for a page to count as 'has text'"),
    password: Optional[str] = None,
):
    """Detect whether a PDF is image-only (scanned) and needs OCR."""
    from .commands import is_scanned_cmd
    is_scanned_cmd.is_scanned_cmd(_file(file), threshold=threshold, password=password)


# ---------------------------------------------------------------------------
# MS Word commands
# ---------------------------------------------------------------------------

@docx_app.command("info")
def docx_info_cmd_run(file: str):
    """Show structure and core properties of a .docx file."""
    from .commands import docx_info_cmd
    docx_info_cmd.info(_file(file))


@docx_app.command("text")
def docx_text_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
):
    """Extract text from a .docx file."""
    from .commands import docx_text_cmd
    docx_text_cmd.text(_file(file), out=_path(out) if out else None)


@docx_app.command("merge")
def docx_merge_cmd_run(
    files: list[str],
    out: str = typer.Option(..., "--out", "-o"),
):
    """Merge multiple .docx files into one."""
    from .commands import docx_merge_cmd
    docx_merge_cmd.merge([_file(f) for f in files], out=_path(out))


@app.command("docx2pdf")
def docx2pdf_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
):
    """Convert a .docx file to PDF (via LibreOffice)."""
    from .commands import docx2pdf_cmd
    docx2pdf_cmd.docx2pdf(_file(file), out=_path(out) if out else None)


@app.command("pdf2docx")
def pdf2docx_cmd_run(
    file: str,
    out: Optional[str] = typer.Option(None, "--out", "-o"),
):
    """Convert a PDF to .docx (via LibreOffice, lossy)."""
    from .commands import pdf2docx_cmd
    pdf2docx_cmd.pdf2docx(_file(file), out=_path(out) if out else None)


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

@app.command("doctor")
def doctor():
    """Show which external tools and Python libraries are available."""
    console.print(BIN.report())


@app.command("version")
def version():
    """Show pdf-tool version."""
    console.print(f"pdf-tool {__version__}")


if __name__ == "__main__":
    app()