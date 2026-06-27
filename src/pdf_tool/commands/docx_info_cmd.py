"""Command: pdf-tool docx info <file.docx>"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..core import docx as core

console = Console()


def info(file: Path) -> None:
    """Show structure and core properties of a .docx file."""
    d = core.docx_info(file)
    console.print(f"\n[bold]{file.name}[/bold]")
    console.print(f"  Paragraphs:  {d['paragraphs']}")
    console.print(f"  Words:       {d['words']}")
    console.print(f"  Images:      {d['images']}")
    props = [
        ("Title", d["title"]),
        ("Author", d["author"]),
        ("Subject", d["subject"]),
        ("Created", d["created"]),
        ("Modified", d["modified"]),
    ]
    console.print("\n[bold]Core properties:[/bold]")
    for k, v in props:
        console.print(f"  {k:<11} {v or '—'}")