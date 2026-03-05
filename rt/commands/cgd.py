"""Create Google Doc command"""

import os
import click
from pathlib import Path
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from rt.config import get_domain
from rt.google_auth import get_drive_service, get_docs_service
from rt.utils import (
    apply_doc_styling,
    copy_to_clipboard,
    create_temp_docx,
    extract_title_from_markdown,
    format_doc_link,
)


@click.command()
@click.argument('markdown_file', type=click.Path(exists=True))
@click.argument('emails', nargs=-1)
@click.option('--name', '-n', help='Custom name for the Google Doc (defaults to extracted title)')
def cgd(markdown_file, emails, name):
    """
    Create Google Doc from markdown file.

    Converts MARKDOWN_FILE to DOCX using pandoc, uploads to Google Drive,
    converts to Google Doc, and sets permissions for ritza.co domain.

    Optionally provide email addresses to share with specific users.

    Examples:
        rt cgd article.md
        rt cgd article.md user@example.com
        rt cgd article.md user1@example.com user2@example.com
    """
    try:
        click.echo(f"Converting {markdown_file} to Google Doc...")

        # Convert markdown to docx
        click.echo("  1. Converting markdown to DOCX with pandoc...")
        docx_path = create_temp_docx(markdown_file)

        # Determine the document name with [External] prefix
        if name is None:
            extracted_title = extract_title_from_markdown(markdown_file)
            name = f"[External] {extracted_title}"
        else:
            name = f"[External] {name}"

        # Get Google Drive service
        click.echo("  2. Authenticating with Google...")
        drive_service = get_drive_service()

        # Upload the DOCX file and convert to Google Doc
        click.echo("  3. Uploading to Google Drive...")
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.document'
        }
        media = MediaFileUpload(
            str(docx_path),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            resumable=True
        )

        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')
        click.echo(f"  4. Google Doc created with ID: {file_id}")

        # Set permissions for configured domain (if any)
        domain = get_domain()
        if domain:
            click.echo(f"  5. Setting permissions for {domain} domain...")
            try:
                drive_service.permissions().create(
                    fileId=file_id,
                    body={'type': 'domain', 'role': 'writer', 'domain': domain},
                    fields='id'
                ).execute()
                click.echo(f"     Permissions set: Anyone at {domain} can edit")
            except HttpError as error:
                click.echo(f"     Warning: Could not set domain permissions: {error}")
        else:
            click.echo("  5. No domain configured — skipping domain permissions.")

        # Set permissions for individual email addresses (without notifications)
        if emails:
            click.echo(f"  5b. Adding {len(emails)} email(s) as editors...")
            for email in emails:
                email_permission = {
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': email
                }
                try:
                    drive_service.permissions().create(
                        fileId=file_id,
                        body=email_permission,
                        sendNotificationEmail=False,
                        supportsAllDrives=True,
                        fields='id'
                    ).execute()
                    click.echo(f"      Added: {email}")
                except HttpError as error:
                    click.echo(f"      Warning: Could not add {email}: {error}")

        # Apply Ritza styling via the Docs API
        click.echo("  6. Applying Ritza styling...")
        try:
            docs_service = get_docs_service()
            apply_doc_styling(docs_service, file_id)
            click.echo("     Fonts, colours, and spacing applied.")
        except Exception as e:
            click.echo(f"     Warning: Could not apply styling: {e}")

        # Clean up temporary DOCX file
        click.echo("  7. Cleaning up temporary files...")
        docx_path.unlink()

        # Format and display the link
        doc_link = format_doc_link(file_id)

        # Copy title and link to clipboard
        click.echo("  8. Copying to clipboard...")
        copy_to_clipboard(name)
        click.echo(f"     Copied title: {name}")
        copy_to_clipboard(doc_link)
        click.echo(f"     Copied link: {doc_link}")

        click.echo()
        click.echo(click.style("Success!", fg='green', bold=True))
        click.echo(f"Title: {name}")
        click.echo(f"Link: {doc_link}")
        click.echo()
        click.echo(click.style("✓ Both title and link copied to clipboard!", fg='cyan'))
        click.echo("  Use your clipboard history to paste them separately.")

    except FileNotFoundError as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        raise click.Abort()
    except RuntimeError as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        raise click.Abort()
    except HttpError as error:
        click.echo(click.style(f"Google API Error: {error}", fg='red'), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(f"Unexpected error: {e}", fg='red'), err=True)
        raise click.Abort()
