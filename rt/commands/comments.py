"""Get comments and suggestions from a Google Doc"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET

import click
from googleapiclient.errors import HttpError

from rt.google_auth import get_drive_service, get_docs_service


def extract_doc_id(url_or_id: str) -> str:
    """Extract file ID from a Google Docs URL or return as-is if already an ID."""
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url_or_id)
    return match.group(1) if match else url_or_id


def get_docx_comments(drive_service, file_id: str) -> list[dict]:
    """
    Export doc as DOCX and parse word/comments.xml.

    This is the reliable way to get ALL comments, including notes attached to
    suggested edits. The Drive API comments endpoint misses suggestion-linked
    comments entirely (they don't appear regardless of permissions or fields
    requested). The DOCX export includes them in word/comments.xml.
    """
    request = drive_service.files().export_media(
        fileId=file_id,
        mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    content = request.execute()

    z = zipfile.ZipFile(io.BytesIO(content))
    if 'word/comments.xml' not in z.namelist():
        return []

    root = ET.fromstring(z.read('word/comments.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    comments = []
    for comment in root.findall('w:comment', ns):
        w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        author = comment.get(f'{{{w}}}author', 'Unknown')
        date = comment.get(f'{{{w}}}date', '')
        text = ''.join(t.text or '' for t in comment.iter(f'{{{w}}}t'))
        if text.strip():
            comments.append({'author': author, 'date': date, 'content': text.strip()})

    return comments


def get_doc_suggestions(docs_service, file_id: str) -> list[dict]:
    """Get tracked changes (suggestions) from the Docs API."""
    doc = docs_service.documents().get(
        documentId=file_id,
        suggestionsViewMode='SUGGESTIONS_INLINE'
    ).execute()

    suggestions = {}
    for elem in doc.get('body', {}).get('content', []):
        for pe in elem.get('paragraph', {}).get('elements', []):
            tr = pe.get('textRun', {})
            content = tr.get('content', '')
            for sid in tr.get('suggestedInsertionIds', []):
                suggestions.setdefault(sid, {'insertions': [], 'deletions': []})
                suggestions[sid]['insertions'].append(content)
            for sid in tr.get('suggestedDeletionIds', []):
                suggestions.setdefault(sid, {'insertions': [], 'deletions': []})
                suggestions[sid]['deletions'].append(content)

    result = []
    for sid, changes in suggestions.items():
        parts = []
        if changes['deletions']:
            parts.append(f"delete: {''.join(changes['deletions']).strip()!r}")
        if changes['insertions']:
            parts.append(f"insert: {''.join(changes['insertions']).strip()!r}")
        result.append({'id': sid, 'summary': ', '.join(parts)})

    return result


@click.command()
@click.argument('doc')
@click.option('--suggestions/--no-suggestions', default=True, help='Show tracked changes')
def comments(doc, suggestions):
    """Show comments and suggestions from a Google Doc.

    DOC can be a full Google Docs URL or just the document ID.

    \b
    Examples:
        rt comments https://docs.google.com/document/d/abc123/edit
        rt comments abc123
    """
    file_id = extract_doc_id(doc)

    try:
        drive_service = get_drive_service()
        docs_service = get_docs_service()
    except FileNotFoundError as e:
        raise click.ClickException(str(e))

    # Comments (including suggestion-linked notes) via DOCX export
    try:
        doc_comments = get_docx_comments(drive_service, file_id)
    except HttpError as e:
        raise click.ClickException(f"Could not fetch document: {e}")

    if doc_comments:
        click.echo(click.style("Comments", bold=True))
        click.echo("─" * 40)
        for c in doc_comments:
            date = c['date'][:10] if c['date'] else ''
            click.echo(click.style(f"{c['author']} ({date})", fg='cyan'))
            click.echo(f"  {c['content']}")
            click.echo()
    else:
        click.echo("No comments found.")

    # Suggestions via Docs API
    if suggestions:
        try:
            doc_suggestions = get_doc_suggestions(docs_service, file_id)
        except HttpError as e:
            raise click.ClickException(f"Could not fetch suggestions: {e}")

        if doc_suggestions:
            click.echo(click.style("Suggestions", bold=True))
            click.echo("─" * 40)
            for s in doc_suggestions:
                click.echo(click.style(f"[{s['id']}]", fg='yellow'))
                click.echo(f"  {s['summary']}")
                click.echo()
