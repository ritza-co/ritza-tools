# ritza-tools (`rt`)

A CLI for working with Google Docs and markdown articles.

```
rt cgd article.md
rt cgd article.md editor@example.com
```

Converts a markdown file to a Google Doc with clean typography (Merriweather font, styled headings, code formatting), sets sharing permissions, and copies the link to your clipboard.

```
rt comments https://docs.google.com/document/d/DOC_ID/edit
```

Prints all comments and tracked changes (suggestions) from a Google Doc.

## Prerequisites

- Python 3.8+
- [pandoc](https://pandoc.org/installing.html)
- A Google Cloud project with the Drive and Docs APIs enabled

### Install pandoc

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt-get install pandoc
```

## Installation

```bash
pipx install git+https://github.com/ritza-co/ritza-tools.git
```

Or clone and install locally:

```bash
git clone https://github.com/ritza-co/ritza-tools.git
cd ritza-tools
pipx install .
```

## Google Cloud setup

You need OAuth credentials so the tool can create files in your Google Drive.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project (or select an existing one)
2. Enable the **Google Drive API** and **Google Docs API**
3. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Choose **Desktop app** as the application type, then download the JSON file
5. Save it to `~/.rt/client_secret.json`:

```bash
mkdir -p ~/.rt
mv ~/Downloads/client_secret_*.json ~/.rt/client_secret.json
```

The first time you run `rt`, a browser window will open asking you to authorise access. Your token is cached at `~/.rt/token.pickle` for subsequent runs.

## Configuration

Create `~/.rt/config.json`:

```bash
mkdir -p ~/.rt
```

```json
{
  "domain": "yourcompany.com"
}
```

If `domain` is set, every created doc is shared with editor access for anyone at that domain. Leave it out (or omit the file entirely) to skip domain sharing.

## Usage

### Create a Google Doc

```bash
rt cgd article.md
```

With a custom title:

```bash
rt cgd article.md --name "My Article Title"
```

Share with specific people (in addition to any domain permission):

```bash
rt cgd article.md editor@example.com reviewer@example.com
```

On success the Google Doc link is printed and copied to your clipboard.

### What it does

1. Converts the markdown file to DOCX using pandoc (with a bundled reference template for clean base styles)
2. Strips pandoc's heading bookmarks so they don't appear in Google Docs
3. Uploads to Google Drive and converts to a Google Doc
4. Sets domain sharing permissions (if configured)
5. Applies typography via the Google Docs API — Merriweather font, branded heading colours, code formatting
6. Copies the link to clipboard

### Get comments and suggestions from a Google Doc

```bash
rt comments https://docs.google.com/document/d/DOC_ID/edit
```

Or with just the document ID:

```bash
rt comments DOC_ID
```

To show only comments (skip the suggestions list):

```bash
rt comments DOC_ID --no-suggestions
```

Outputs all comments and tracked changes. Comments include notes attached to suggested edits, which are not available through the Drive API (see below).

---

#### How Google Doc comments actually work (and why the Drive API misses some)

Google Docs has three layers of reviewer feedback, all of which look similar in the UI:

**1. Regular comments** (`Insert → Comment`)
Standard Drive comments, returned by `GET /drive/v3/files/{id}/comments`. Straightforward.

**2. Tracked changes / suggestions**
Edits made in Suggesting mode. These are stored inside the document content itself (not in Drive comments), accessible via the Docs API with `suggestionsViewMode=SUGGESTIONS_INLINE`. Each changed run has a `suggestedInsertionIds` or `suggestedDeletionIds` field containing an opaque suggestion ID.

**3. Notes attached to suggestions**
When a reviewer makes a tracked change, they can optionally type an explanatory note. In the UI this appears as a comment bubble alongside the suggestion. Internally it is a Drive comment with an `anchor` field pointing to the suggestion range.

The problem: **the Drive API `comments.list` endpoint does not return these**, even with `fields=comments(id,content,anchor,...)` explicitly set and editor-level access on the file. This appears to be a gap in the API rather than a permissions issue — the same result occurs regardless of whether you authenticate as a service account or as the document owner.

**The workaround: DOCX export**

Exporting the document as DOCX and unzipping `word/comments.xml` gives you all comments including suggestion-linked notes, because the DOCX format stores them as standard `<w:comment>` elements. This is what `rt comments` uses:

```python
request = drive_service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
content = request.execute()
z = zipfile.ZipFile(io.BytesIO(content))
root = ET.fromstring(z.read('word/comments.xml'))
```

---

## Re-authenticating

If your token expires or you want to switch accounts:

```bash
rm ~/.rt/token.pickle
rt cgd article.md   # will re-open browser auth
```

## Updating the reference template

The bundled `rt/reference.docx` controls base DOCX styles (code block shading, heading borders, etc.). To regenerate it after making style changes:

```bash
pip install python-docx
python create_reference.py
pipx install --force .
```
