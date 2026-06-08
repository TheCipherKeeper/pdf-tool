# pdf-tool

A Swiss-army CLI for working with PDFs: split, merge, compress, OCR, optimize, extract images/text, render previews, and rearrange pages.

Built on top of [Ghostscript](https://www.ghostscript.com/), [qpdf](https://qpdf.sourceforge.io/), [tesseract](https://github.com/tesseract-ocr/tesseract), [poppler](https://poppler.freedesktop.org/), and [PyMuPDF](https://pymupdf.readthedocs.io/).

## Install

```bash
# 1. Install the package globally
uv tool install .

# 2. Verify
pdf-tool doctor
pdf-tool version
```

> If `uv tool install .` fails because the project directory is on Desktop and locked, use `uv tool install --reinstall .` to refresh.

## Commands

| Command | What it does |
|---|---|
| `pdf-tool info FILE` | Show metadata, page count, image inventory |
| `pdf-tool images FILE [--extract]` | List or extract all images |
| `pdf-tool text FILE [-l]` | Extract text (poppler's pdftotext) |
| `pdf-tool optimize FILE [--linearize]` | Lossless recompress via qpdf |
| `pdf-tool compress FILE [--preset ebook]` | Compress via ghostscript (4 presets + custom q/dpi) |
| `pdf-tool compress FILE --target-size 4MB` | Auto-pick highest quality that fits a target size |
| `pdf-tool split FILE -n 3 -m 4MB` | Split into N parts of <= max-size, max quality |
| `pdf-tool merge a.pdf b.pdf -o out.pdf` | Concatenate PDFs with bookmarks |
| `pdf-tool rearrange FILE -p 1,3-5,2 -o out.pdf` | Reorder/remove/duplicate pages |
| `pdf-tool preview FILE [-p 1-3] -o dir/` | Render pages to PNG/JPEG |
| `pdf-tool ocr FILE -o out.pdf` | Run tesseract on a scanned PDF |
| `pdf-tool doctor` | Show which external tools are available |

## Examples

```bash
# Show info about a PDF
pdf-tool info Doc.pdf

# Extract all images
pdf-tool images Doc.pdf --extract -o ./imgs

# Get text
pdf-tool text Doc.pdf -l -o text.txt

# Compress with a preset
pdf-tool compress Doc.pdf -o small.pdf -p ebook

# Compress to a specific size, picking best quality
pdf-tool compress Doc.pdf --target-size 4MB

# Split into 3 parts, each <= 4MB
pdf-tool split Doc.pdf -n 3 -m 4MB

# Merge
pdf-tool merge a.pdf b.pdf c.pdf -o all.pdf

# Rearrange
pdf-tool rearrange Doc.pdf -p 1,3-5,2 -o reordered.pdf

# Render previews
pdf-tool preview Doc.pdf -p 1-3 -o ./previews --dpi 150

# OCR a scanned PDF
pdf-tool ocr scanned.pdf -o searchable.pdf -l rus+eng

# Optimize (lossless)
pdf-tool optimize Doc.pdf -L --remove-metadata
```

## Required external tools

| Tool | Used by | Install |
|---|---|---|
| Ghostscript | `compress`, `split` | https://www.ghostscript.com/ |
| qpdf | `optimize` | https://qpdf.sourceforge.io/ |
| tesseract | `ocr` | https://github.com/tesseract-ocr/tesseract |
| poppler | `text` | https://poppler.freedesktop.org/ |
| PyMuPDF | `preview`, `images` (bundled) | installed via pip |
| pypdf, pikepdf | most commands (bundled) | installed via pip |

`pdf-tool doctor` shows which are detected.

## Size units

Wherever a size is accepted (`--max-size`, `--target-size`), you can use:

- `4MB`, `500KB`, `1GB` (powers of 1024)
- Or just bytes: `4194304`

## Quality ladder used by `split` and `--target-size`

`pdf-tool` searches the (JPEG quality, image DPI) ladder from highest to lowest quality:

```
(98,300) (95,300) (92,300) (90,300) (90,250) (90,200) (88,200) (85,200)
(85,180) (85,160) (85,150) (82,150) (80,150) (80,130) (78,130) (75,120)
```

The first setting that fits the target is used. This is the strategy that worked best on real-world scanned documents with embedded photographs.
