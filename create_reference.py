#!/usr/bin/env python3
"""
Generate a styled pandoc reference.docx for rt-cli.
Run this script to regenerate rt/reference.docx after changing styles.

Usage: python3 create_reference.py
Requires: python-docx (pip install python-docx)
"""

import subprocess
import shutil
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


OUTPUT_PATH = Path(__file__).parent / 'rt' / 'reference.docx'


def set_shading(pPr, fill_hex: str):
    """Add or update w:shd on a pPr element."""
    shd = pPr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd')
        pPr.append(shd)
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)


def remove_paragraph_border(style):
    """Remove all paragraph borders from a style."""
    pPr = style.element.get_or_add_pPr()
    pBdr = pPr.find(qn('w:pBdr'))
    if pBdr is not None:
        pPr.remove(pBdr)


def set_style_shading(style, fill_hex: str):
    """Add shading to a paragraph style."""
    pPr = style.element.get_or_add_pPr()
    set_shading(pPr, fill_hex)


def set_paragraph_indent(style, left_twips=0, first_line_twips=0):
    """Set paragraph indentation (in twips: 1 inch = 1440 twips)."""
    pPr = style.element.get_or_add_pPr()
    ind = pPr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        pPr.append(ind)
    ind.set(qn('w:left'), str(left_twips))
    ind.set(qn('w:firstLine'), str(first_line_twips))


def main():
    # Generate base reference.docx from pandoc
    tmp_path = Path('/tmp/rt_base_reference.docx')
    print("Generating base reference.docx from pandoc...")
    subprocess.run(
        ['pandoc', '--print-default-data-file', 'reference.docx'],
        stdout=open(tmp_path, 'wb'),
        check=True
    )

    print(f"Modifying styles...")
    doc = Document(str(tmp_path))

    styles = doc.styles

    # ── Normal / Body Text ──────────────────────────────────────────────────
    for style_name in ('Normal', 'Body Text', 'First Paragraph'):
        try:
            s = styles[style_name]
            s.font.name = 'Georgia'
            s.font.size = Pt(11)
            s.paragraph_format.space_before = Pt(0)
            s.paragraph_format.space_after = Pt(10)
            set_paragraph_indent(s, left_twips=0, first_line_twips=0)
        except KeyError:
            pass

    # ── Headings ────────────────────────────────────────────────────────────
    heading_cfg = {
        'Heading 1': (20, RGBColor(0x1e, 0x32, 0x59), 20, 6),
        'Heading 2': (16, RGBColor(0x33, 0x58, 0x88), 16, 4),
        'Heading 3': (13, RGBColor(0x49, 0x72, 0xa1), 12, 4),
        'Heading 4': (11, RGBColor(0x49, 0x72, 0xa1), 10, 2),
    }
    for name, (size, color, before, after) in heading_cfg.items():
        try:
            s = styles[name]
            s.font.name = 'Georgia'
            s.font.size = Pt(size)
            s.font.bold = True
            s.font.color.rgb = color
            s.paragraph_format.space_before = Pt(before)
            s.paragraph_format.space_after = Pt(after)
            remove_paragraph_border(s)
            set_paragraph_indent(s, left_twips=0, first_line_twips=0)
        except KeyError:
            pass

    # ── Source Code (pandoc code block style) ───────────────────────────────
    for style_name in ('Source Code', 'Verbatim', 'Code'):
        try:
            s = styles[style_name]
            s.font.name = 'Courier New'
            s.font.size = Pt(9.5)
            s.paragraph_format.space_before = Pt(4)
            s.paragraph_format.space_after = Pt(4)
            set_style_shading(s, 'F3F4F6')  # light gray
            set_paragraph_indent(s, left_twips=360, first_line_twips=0)  # 0.25 inch indent
        except KeyError:
            pass

    # ── Verbatim Char (pandoc inline code style) ────────────────────────────
    try:
        s = styles['Verbatim Char']
        s.font.name = 'Courier New'
        s.font.size = Pt(10)
    except KeyError:
        pass

    # ── Block Text (blockquotes) ─────────────────────────────────────────────
    try:
        s = styles['Block Text']
        s.font.name = 'Georgia'
        s.font.italic = True
        s.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        s.paragraph_format.space_before = Pt(8)
        s.paragraph_format.space_after = Pt(8)
        set_paragraph_indent(s, left_twips=720, first_line_twips=0)  # 0.5 inch
    except KeyError:
        pass

    doc.save(str(OUTPUT_PATH))
    tmp_path.unlink()
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
