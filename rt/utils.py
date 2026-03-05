"""Helper utilities for rt CLI"""

import os
import re
import subprocess
import shutil
import zipfile
from pathlib import Path

# Path to pandoc reference.docx bundled with this package
REFERENCE_DOCX = Path(__file__).parent / 'reference.docx'


def check_pandoc_installed():
    """
    Check if pandoc is installed and available in PATH

    Returns:
        bool: True if pandoc is installed, False otherwise
    """
    return shutil.which('pandoc') is not None


def create_temp_docx(md_file):
    """
    Convert markdown file to DOCX using pandoc

    Args:
        md_file: Path to the markdown file

    Returns:
        Path to the created DOCX file

    Raises:
        RuntimeError: If pandoc is not installed
        subprocess.CalledProcessError: If pandoc conversion fails
    """
    if not check_pandoc_installed():
        raise RuntimeError(
            "pandoc is not installed.\n\n"
            "To install pandoc:\n"
            "  macOS:   brew install pandoc\n"
            "  Ubuntu:  sudo apt-get install pandoc\n"
            "  Windows: Download from https://pandoc.org/installing.html"
        )

    md_path = Path(md_file)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    docx_path = md_path.with_suffix('.docx')

    cmd = ['pandoc', str(md_path), '-o', str(docx_path)]
    if REFERENCE_DOCX.exists():
        cmd += ['--reference-doc', str(REFERENCE_DOCX)]

    subprocess.run(cmd, check=True, capture_output=True, text=True)

    _strip_bookmarks(docx_path)

    return docx_path


def _strip_bookmarks(docx_path):
    """
    Remove pandoc bookmark elements from a DOCX file in-place.

    pandoc adds <w:bookmarkStart> and <w:bookmarkEnd> to every heading for
    internal cross-references. These show up as bookmark icons in Google Docs.
    """
    tmp_path = docx_path.with_suffix('.tmp.docx')
    with zipfile.ZipFile(docx_path, 'r') as zin:
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == 'word/document.xml':
                    xml = data.decode('utf-8')
                    xml = re.sub(r'<w:bookmarkStart\b[^>]*/>', '', xml)
                    xml = re.sub(r'<w:bookmarkEnd\b[^>]*/>', '', xml)
                    data = xml.encode('utf-8')
                zout.writestr(item, data)
    tmp_path.replace(docx_path)


def format_doc_link(file_id):
    """
    Format Google Docs URL from file ID

    Args:
        file_id: Google Drive file ID

    Returns:
        Full Google Docs URL
    """
    return f"https://docs.google.com/document/d/{file_id}/edit"


def extract_title_from_markdown(md_file):
    """
    Extract title from markdown file using:
    1. YAML frontmatter title field
    2. First heading (# Heading)
    3. Filename with hyphens replaced by spaces

    Args:
        md_file: Path to the markdown file

    Returns:
        Extracted title string
    """
    md_path = Path(md_file)

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Try to extract from YAML frontmatter
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if yaml_match:
        yaml_content = yaml_match.group(1)
        title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', yaml_content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()

    # Try to extract first heading
    heading_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    # Fallback to filename with hyphens replaced by spaces
    filename = md_path.stem
    title = filename.replace('-', ' ').replace('_', ' ')
    title = ' '.join(word.capitalize() for word in title.split())

    return title


def copy_to_clipboard(text):
    """
    Copy text to macOS clipboard using pbcopy

    Args:
        text: Text to copy to clipboard
    """
    process = subprocess.Popen(
        ['pbcopy'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    process.communicate(input=text.encode('utf-8'))
    process.wait()


def apply_doc_styling(docs_service, file_id):
    """
    Apply Ritza brand styling to an uploaded Google Doc via the Docs API.

    Iterates through every paragraph and applies fonts, colours, and spacing
    based on its named style type (headings vs body text). Code runs are
    re-styled last so they override the body font.

    Args:
        docs_service: Google Docs API service object
        file_id: Google Doc file ID
    """
    # Brand colours as 0–1 RGB floats
    dark_blue  = {'red': 0.118, 'green': 0.196, 'blue': 0.353}  # #1e3259
    mid_blue   = {'red': 0.200, 'green': 0.345, 'blue': 0.533}  # #335888
    light_blue = {'red': 0.286, 'green': 0.447, 'blue': 0.631}  # #4972a1
    body_gray  = {'red': 0.133, 'green': 0.133, 'blue': 0.133}  # #222222
    code_green = {'red': 0.133, 'green': 0.373, 'blue': 0.255}  # #226040

    def color(rgb):
        return {'color': {'rgbColor': rgb}}

    merriweather = {'fontFamily': 'Merriweather', 'weight': 400}
    merriweather_bold = {'fontFamily': 'Merriweather', 'weight': 700}
    courier = {'fontFamily': 'Courier New', 'weight': 400}

    heading_cfg = {
        'HEADING_1': {
            'text': {
                'bold': True,
                'weightedFontFamily': merriweather_bold,
                'fontSize': {'magnitude': 22, 'unit': 'PT'},
                'foregroundColor': color(dark_blue),
            },
            'text_fields': 'bold,weightedFontFamily,fontSize,foregroundColor',
            'para': {
                'lineSpacing': 110,
                'spaceAbove': {'magnitude': 22, 'unit': 'PT'},
                'spaceBelow': {'magnitude': 6,  'unit': 'PT'},
                'indentFirstLine': {'magnitude': 0, 'unit': 'PT'},
                'indentStart':     {'magnitude': 0, 'unit': 'PT'},
            },
            'para_fields': 'lineSpacing,spaceAbove,spaceBelow,indentFirstLine,indentStart',
        },
        'HEADING_2': {
            'text': {
                'bold': True,
                'weightedFontFamily': merriweather_bold,
                'fontSize': {'magnitude': 17, 'unit': 'PT'},
                'foregroundColor': color(mid_blue),
            },
            'text_fields': 'bold,weightedFontFamily,fontSize,foregroundColor',
            'para': {
                'lineSpacing': 110,
                'spaceAbove': {'magnitude': 18, 'unit': 'PT'},
                'spaceBelow': {'magnitude': 4,  'unit': 'PT'},
                'indentFirstLine': {'magnitude': 0, 'unit': 'PT'},
                'indentStart':     {'magnitude': 0, 'unit': 'PT'},
            },
            'para_fields': 'lineSpacing,spaceAbove,spaceBelow,indentFirstLine,indentStart',
        },
        'HEADING_3': {
            'text': {
                'bold': True,
                'weightedFontFamily': merriweather_bold,
                'fontSize': {'magnitude': 14, 'unit': 'PT'},
                'foregroundColor': color(light_blue),
            },
            'text_fields': 'bold,weightedFontFamily,fontSize,foregroundColor',
            'para': {
                'lineSpacing': 110,
                'spaceAbove': {'magnitude': 14, 'unit': 'PT'},
                'spaceBelow': {'magnitude': 4,  'unit': 'PT'},
                'indentFirstLine': {'magnitude': 0, 'unit': 'PT'},
                'indentStart':     {'magnitude': 0, 'unit': 'PT'},
            },
            'para_fields': 'lineSpacing,spaceAbove,spaceBelow,indentFirstLine,indentStart',
        },
    }

    doc = docs_service.documents().get(documentId=file_id).execute()
    content = doc.get('body', {}).get('content', [])

    requests = [
        {
            'updateDocumentStyle': {
                'documentStyle': {
                    'marginTop':    {'magnitude': 72, 'unit': 'PT'},
                    'marginBottom': {'magnitude': 72, 'unit': 'PT'},
                    'marginLeft':   {'magnitude': 72, 'unit': 'PT'},
                    'marginRight':  {'magnitude': 72, 'unit': 'PT'},
                },
                'fields': 'marginTop,marginBottom,marginLeft,marginRight',
            }
        },
    ]

    # Code run requests are applied last so they override the body font
    code_requests = []

    def walk(elements):
        for elem in elements:
            if 'paragraph' not in elem:
                if 'table' in elem:
                    for row in elem['table'].get('tableRows', []):
                        for cell in row.get('tableCells', []):
                            walk(cell.get('content', []))
                continue

            para = elem['paragraph']
            named = para.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
            start = elem.get('startIndex', 0)
            end   = elem.get('endIndex', 0)

            if end <= start + 1:  # empty paragraph
                continue

            r = {'startIndex': start, 'endIndex': end - 1}

            if named in heading_cfg:
                cfg = heading_cfg[named]
                requests.append({
                    'updateParagraphStyle': {
                        'range': r,
                        'paragraphStyle': cfg['para'],
                        'fields': cfg['para_fields'],
                    }
                })
                requests.append({
                    'updateTextStyle': {
                        'range': r,
                        'textStyle': cfg['text'],
                        'fields': cfg['text_fields'],
                    }
                })
            else:
                # Body text — only set font family to preserve inline bold/italic
                has_bullet = 'bullet' in para
                if not has_bullet:
                    requests.append({
                        'updateParagraphStyle': {
                            'range': r,
                            'paragraphStyle': {
                                'lineSpacing': 130,
                                'spaceBelow': {'magnitude': 10, 'unit': 'PT'},
                                'indentFirstLine': {'magnitude': 0, 'unit': 'PT'},
                                'indentStart':     {'magnitude': 0, 'unit': 'PT'},
                            },
                            'fields': 'lineSpacing,spaceBelow,indentFirstLine,indentStart',
                        }
                    })
                requests.append({
                    'updateTextStyle': {
                        'range': r,
                        'textStyle': {
                            'weightedFontFamily': merriweather,
                            'fontSize': {'magnitude': 11, 'unit': 'PT'},
                            'foregroundColor': color(body_gray),
                        },
                        'fields': 'weightedFontFamily,fontSize,foregroundColor',
                    }
                })

                # Collect code runs to re-apply after body font is set
                for pe in para.get('elements', []):
                    if 'textRun' not in pe:
                        continue
                    ts = pe['textRun'].get('textStyle', {})
                    font = (ts.get('weightedFontFamily') or {}).get('fontFamily', '')
                    if font in _MONO_FONTS:
                        code_requests.append({
                            'updateTextStyle': {
                                'range': {
                                    'startIndex': pe['startIndex'],
                                    'endIndex':   pe['endIndex'],
                                },
                                'textStyle': {
                                    'weightedFontFamily': courier,
                                    'fontSize': {'magnitude': 10, 'unit': 'PT'},
                                    'foregroundColor': color(code_green),
                                },
                                'fields': 'weightedFontFamily,fontSize,foregroundColor',
                            }
                        })

    walk(content)

    all_requests = requests + code_requests
    for i in range(0, len(all_requests), 500):
        docs_service.documents().batchUpdate(
            documentId=file_id,
            body={'requests': all_requests[i:i + 500]},
        ).execute()


# Monospace fonts pandoc uses for code
_MONO_FONTS = {
    'Courier New', 'Courier', 'Consolas', 'Lucida Console',
    'Monaco', 'Source Code Pro', 'DejaVu Sans Mono',
}
