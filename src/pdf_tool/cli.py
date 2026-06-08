"""pdf-tool: a Swiss-army CLI for PDF manipulation."""
from __future__ import annotations

import typer
from rich.console import Console

from . import __version__
from .backends import BIN
from .commands import (
    compress_cmd,
    images_cmd,
    info_cmd,
    merge_cmd,
    ocr_cmd,
    optimize_cmd,
    preview_cmd,
    rearrange_cmd,
    split_cmd,
    text_cmd,
)

app = typer.Typer(
    name="pdf-tool",
    help="Swiss-army CLI for PDF: split, merge, compress, OCR, optimize, and more.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)
console = Console()


@app.command("info")
def info_cmd_run(file: str, fonts: bool = False):
    """Show metadata and structure of a PDF."""
    info_cmd.info(__resolve_path(file), show_fonts=fonts)


@app.command("images")
def images_cmd_run(
    file: str,
    extract: bool = typer.Option(False, "--extract", "-e"),
    out: str = typer.Option("images", "--out", "-o"),
    min_size: int = typer.Option(0, "--min-size"),
):
    """List or extract all images in a PDF."""
    images_cmd.images(__resolve_path(file), extract=extract, out_dir=__resolve_path(out), min_size=min_size)


@app.command("text")
def text_cmd_run(
    file: str,
    layout: bool = typer.Option(False, "--layout", "-l"),
    out: str = typer.Option(None, "--out", "-o"),
    pages: str = typer.Option(None, "--pages", "-p"),
):
    """Extract text from a PDF (via poppler's pdftotext)."""
    text_cmd.text(
        __resolve_path(file),
        layout=layout,
        out=__resolve_path(out) if out else None,
        pages=pages,
    )


@app.command("optimize")
def optimize_cmd_run(
    file: str,
    out: str = typer.Option(None, "--out", "-o"),
    linearize: bool = typer.Option(False, "--linearize", "-L"),
    compress_streams: bool = True,
    object_streams: bool = True,
    remove_metadata: bool = False,
):
    """Lossless optimization via qpdf."""
    optimize_cmd.optimize(
        __resolve_path(file),
        out=__resolve_path(out) if out else None,
        linearize=linearize,
        compress_streams=compress_streams,
        object_streams=object_streams,
        remove_metadata=remove_metadata,
    )


@app.command("compress")
def compress_cmd_run(
    file: str,
    out: str = typer.Option(None, "--out", "-o"),
    preset: str = typer.Option("ebook", "--preset", "-p"),
    target_size: str = typer.Option(None, "--target-size"),
    jpeg_q: int = typer.Option(None, "--jpeg-q"),
    dpi: int = typer.Option(None, "--dpi"),
):
    """Compress a PDF with ghostscript."""
    compress_cmd.compress(
        __resolve_path(file),
        out=__resolve_path(out) if out else None,
        preset=preset,
        target_size=target_size,
        jpeg_q=jpeg_q,
        dpi=dpi,
    )


@app.command("split")
def split_cmd_run(
    file: str,
    parts: int = typer.Option(..., "--parts", "-n"),
    max_size: str = typer.Option("4MB", "--max-size", "-m"),
    out_dir: str = typer.Option(None, "--out-dir", "-d"),
    prefix: str = typer.Option(None, "--prefix", "-p"),
):
    """Split a PDF into N parts of <= max-size (auto-pick best quality)."""
    split_cmd.split(
        __resolve_path(file),
        parts=parts,
        max_size=max_size,
        out_dir=__resolve_path(out_dir) if out_dir else None,
        prefix=prefix,
    )


@app.command("merge")
def merge_cmd_run(
    files: list[str],
    out: str = typer.Option(..., "--out", "-o"),
    bookmarks: bool = True,
):
    """Merge multiple PDFs into one."""
    merge_cmd.merge([__resolve_path(f) for f in files], out=__resolve_path(out), bookmarks=bookmarks)


@app.command("rearrange")
def rearrange_cmd_run(
    file: str,
    pages: str = typer.Option(..., "--pages", "-p"),
    out: str = typer.Option(..., "--out", "-o"),
):
    """Reorder/remove/duplicate pages in a PDF."""
    rearrange_cmd.rearrange(__resolve_path(file), pages=pages, out=__resolve_path(out))


@app.command("preview")
def preview_cmd_run(
    file: str,
    out_dir: str = typer.Option("previews", "--out", "-o"),
    pages: str = typer.Option(None, "--pages", "-p"),
    dpi: int = 150,
    fmt: str = typer.Option("png", "--format", "-f"),
):
    """Render pages of a PDF to PNG/JPEG images."""
    preview_cmd.preview(
        __resolve_path(file),
        out_dir=__resolve_path(out_dir),
        pages=pages,
        dpi=dpi,
        fmt=fmt,
    )


@app.command("ocr")
def ocr_cmd_run(
    file: str,
    out: str = typer.Option(..., "--out", "-o"),
    lang: str = typer.Option("rus+eng", "--lang", "-l"),
    dpi: int = 300,
    pages: str = typer.Option(None, "--pages", "-p"),
):
    """OCR a scanned PDF (tesseract) into a searchable PDF."""
    ocr_cmd.ocr(
        __resolve_path(file),
        out=__resolve_path(out),
        lang=lang,
        dpi=dpi,
        pages=pages,
    )


@app.command("doctor")
def doctor():
    """Show which external tools are available."""
    console.print(BIN.report())


@app.command("version")
def version():
    """Show pdf-tool version."""
    console.print(f"pdf-tool {__version__}")


def __resolve_path(s: str) -> "Path":
    from pathlib import Path
    return Path(s).expanduser().resolve()


if __name__ == "__main__":
    app()
