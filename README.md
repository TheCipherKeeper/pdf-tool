# pdf-tool

A Swiss-army CLI for working with **PDFs and MS Word**: split, merge, compress, OCR, convert, rotate, encrypt, watermark, repair, and more.

Built on top of [Ghostscript](https://www.ghostscript.com/), [qpdf](https://qpdf.sourceforge.io/), [tesseract](https://github.com/tesseract-ocr/tesseract), [poppler](https://poppler.freedesktop.org/), [PyMuPDF](https://pymupdf.readthedocs.io/), [pypdf](https://github.com/py-pdf/pypdf), [pikepdf](https://github.com/pikepdf/pikepdf), [python-docx](https://github.com/python-openxml/python-docx), and [LibreOffice](https://www.libreoffice.org/) (for Word↔PDF conversion).

## Install

```bash
# 1. Install the package (editable) into a virtualenv
uv pip install -e .

# 2. Verify external tools and Python libraries
pdf-tool doctor
pdf-tool version
```

> `pdf-tool doctor` reports which external binaries and Python libraries are available and which features they unlock.

## Commands

### PDF

| Command | What it does |
|---|---|
| `pdf-tool info FILE [--fonts]` | Show metadata, page count, image inventory, (fonts) |
| `pdf-tool images FILE [--extract] [-o dir]` | List or extract all images (any colorspace) |
| `pdf-tool text FILE [-l] [-p 1,3,8-10] [-o out.txt]` | Extract text (poppler, with pypdf fallback) |
| `pdf-tool optimize FILE [-L] [--remove-metadata] [-o out]` | Lossless recompress via qpdf (default: overwrite input) |
| `pdf-tool compress FILE [--preset ebook]` | Compress via ghostscript (4 presets + custom q/dpi) |
| `pdf-tool compress FILE --target-size 4MB` | Auto-pick highest quality that fits a target size |
| `pdf-tool split FILE -n 3 -m 4MB` | Split into N parts of <= max-size, max quality |
| `pdf-tool merge a.pdf b.pdf -o out.pdf` | Concatenate PDFs with a parent bookmark per file |
| `pdf-tool rearrange FILE -p 1,3-5,2 -o out.pdf` | Reorder/remove/duplicate pages |
| `pdf-tool preview FILE [-p 1-3] -o dir/` | Render pages to PNG/JPEG |
| `pdf-tool ocr FILE -o out.pdf [-l rus+eng]` | Run tesseract on a scanned PDF |
| `pdf-tool rotate FILE -a 90 [-p 1-3] -o out.pdf` | Rotate pages (90/180/270) |
| `pdf-tool extract FILE -p 1-5 -o out.pdf` | Extract a page subset |
| `pdf-tool delete FILE -p 3,7 -o out.pdf` | Remove pages |
| `pdf-tool encrypt FILE --user-pw X [--owner-pw Y] -o out.pdf` | Apply 256-bit AES encryption |
| `pdf-tool decrypt FILE --password X -o out.pdf` | Remove encryption |
| `pdf-tool metadata FILE [--title ... --author ...] / --strip -o out.pdf` | Set or strip metadata |
| `pdf-tool watermark FILE --text "DRAFT" -o out.pdf` | Diagonal text watermark on every page |
| `pdf-tool repair FILE -o out.pdf` | Recover a damaged PDF (pikepdf → qpdf fallback) |

Most PDF commands accept `--password` for encrypted inputs.

### MS Word

| Command | What it does |
|---|---|
| `pdf-tool docx info FILE.docx` | Paragraph/word/image counts + core properties |
| `pdf-tool docx text FILE.docx [-o out.txt]` | Extract text (paragraphs + tables) |
| `pdf-tool docx merge a.docx b.docx -o out.docx` | Concatenate .docx files (page break between) |
| `pdf-tool docx2pdf FILE.docx -o out.pdf` | Convert .docx → PDF (LibreOffice) |
| `pdf-tool pdf2docx FILE.pdf -o out.docx` | Convert PDF → .docx (LibreOffice, lossy) |

> `docx2pdf` / `pdf2docx` require LibreOffice (`soffice`). If it's missing, `doctor` says so and the commands exit with a clear install hint instead of a crash.

## Examples

```bash
# Show info about a PDF
pdf-tool info Doc.pdf

# Extract all images (works on RGB, Gray, and CMYK images)
pdf-tool images Doc.pdf --extract -o ./imgs

# Extract only pages 1, 3, and 8-10 (true discrete selection)
pdf-tool text Doc.pdf -p 1,3,8-10 -o text.txt

# Compress to a specific size, picking best quality
pdf-tool compress Doc.pdf --target-size 4MB

# Split into 3 parts, each <= 4MB
pdf-tool split Doc.pdf -n 3 -m 4MB

# Merge with bookmarks
pdf-tool merge a.pdf b.pdf c.pdf -o all.pdf

# Rotate every page 90°
pdf-tool rotate Doc.pdf -a 90 -o rotated.pdf

# Encrypt, then decrypt
pdf-tool encrypt Doc.pdf --user-pw s3cret -o locked.pdf
pdf-tool decrypt locked.pdf --password s3cret -o unlocked.pdf

# Watermark and repair
pdf-tool watermark Doc.pdf --text "DRAFT" -o wm.pdf
pdf-tool repair damaged.pdf -o fixed.pdf

# MS Word
pdf-tool docx text Notes.docx -o notes.txt
pdf-tool docx merge part1.docx part2.docx -o combined.docx
pdf-tool docx2pdf Report.docx -o Report.pdf
```

## Required external tools

| Tool | Used by | Install |
|---|---|---|
| Ghostscript | `compress`, `split` | https://www.ghostscript.com/ (also bundled with PDF24) |
| qpdf | `optimize`, `repair` | https://qpdf.sourceforge.io/ (also bundled with PDF24) |
| tesseract | `ocr` | https://github.com/tesseract-ocr/tesseract (also bundled with PDF24) |
| poppler | `text` | https://poppler.freedesktop.org/ (pypdf fallback if missing) |
| LibreOffice | `docx2pdf`, `pdf2docx` | https://www.libreoffice.org/ |
| PyMuPDF, pypdf, pikepdf, python-docx, cryptography | most commands (bundled, installed via pip) | — |

`pdf-tool doctor` shows which are detected.

## Size units

Wherever a size is accepted (`--max-size`, `--target-size`), you can use:

- `4MB`, `500KB`, `1GB` (powers of 1024)
- Or just bytes: `4194304`

## Quality ladder used by `split` and `--target-size`

`pdf-tool` searches the (JPEG quality, image DPI) ladder from highest to lowest quality; the first setting that fits the target is used.

## Tests

```bash
uv pip install -e ".[dev]"   # installs pytest
python -m pytest -q
```

The suite builds its own tiny PDF/docx fixtures in-memory, so it runs anywhere the Python dependencies are installed — no binary assets, no external tools required for most tests.