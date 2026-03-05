# ritza-tools (`rt`)

A CLI for converting markdown articles to styled Google Docs.

```
rt cgd article.md
rt cgd article.md editor@example.com
```

Converts a markdown file to a Google Doc with clean typography (Merriweather font, styled headings, code formatting), sets sharing permissions, and copies the link to your clipboard.

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
