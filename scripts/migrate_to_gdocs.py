#!/usr/bin/env python3
"""
Migrate journal entries from DOCX files to Google Docs.

This script:
1. Parses existing DOCX files using parse_docx.py
2. Creates Google Docs via API for each source file
3. Formats entries with date headers and [[image: ...]] tags
4. Uploads images to Google Drive folders
5. Organizes docs into year folders

Usage (OAuth - creates files in YOUR Drive):
    python scripts/migrate_to_gdocs.py --oauth --folder-id FOLDER_ID

Usage (Service Account - creates files in service account's Drive):
    python scripts/migrate_to_gdocs.py --credentials credentials.json --folder-id FOLDER_ID
"""

import argparse
import io
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PIL import Image
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Import from existing parse_docx module
import sys
sys.path.insert(0, str(Path(__file__).parent))
from parse_docx import find_docx_files, parse_docx_file, JournalEntry, ParsedDocument

console = Console()


# Google Docs batch update limit
BATCH_LIMIT = 100


def get_month_from_doc_title(title: str) -> str:
    """Extract month from document title like 'July 1983'."""
    # This is a placeholder - actual implementation depends on your DOCX naming
    return title


class GDocsMigrator:
    """Migrator for DOCX to Google Docs."""

    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive',
    ]

    def __init__(self, credentials_path: str = None, root_folder_id: str = None, use_oauth: bool = False):
        """
        Initialize the migrator.

        Args:
            credentials_path: Path to service account credentials JSON (if not using OAuth)
            root_folder_id: Root Google Drive folder ID for journal
            use_oauth: If True, use OAuth flow (personal credentials) instead of service account
        """
        self.root_folder_id = root_folder_id
        self.project_root = Path.cwd()
        self.use_oauth = use_oauth

        # Authenticate
        if use_oauth:
            self.creds = self._get_oauth_credentials()
        else:
            self.creds = ServiceAccountCredentials.from_service_account_file(
                credentials_path,
                scopes=self.SCOPES
            )

        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

        # Cache for folder IDs
        self._year_folders: dict[str, str] = {}
        self._images_folders: dict[str, str] = {}
        self._root_images_folder: Optional[str] = None

        console.print("[green]Authenticated with Google APIs[/green]")

    def _get_oauth_credentials(self) -> Credentials:
        """
        Get OAuth credentials for user authentication.

        Uses token.json to store credentials, or runs OAuth flow if needed.
        """
        token_path = self.project_root / "token.json"
        creds = None

        # Load existing token if available
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Need to run OAuth flow
                from google_auth_oauthlib.flow import InstalledAppFlow

                console.print("\n[yellow]OAuth flow required for first-time setup.[/yellow]")
                console.print("1. Go to https://console.cloud.google.com/apis/credentials")
                console.print("2. Create OAuth 2.0 credentials (Desktop app)")
                console.print("3. Download client_secret.json and save it in the project root\n")

                client_secret = self.project_root / "client_secret.json"
                if not client_secret.exists():
                    console.print("[red]client_secret.json not found![/red]")
                    console.print("\nTo create OAuth credentials:")
                    console.print("  1. Go to https://console.cloud.google.com/apis/credentials")
                    console.print("  2. Click 'Create Credentials' → 'OAuth client ID'")
                    console.print("  3. Application type: 'Desktop app'")
                    console.print("  4. Download and save as client_secret.json")
                    raise FileNotFoundError("client_secret.json not found")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secret), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

            console.print(f"[green]Credentials saved to {token_path}[/green]")

        return creds

    def _get_or_create_year_folder(self, year: int) -> str:
        """Get or create a folder for a given year."""
        if year in self._year_folders:
            return self._year_folders[year]

        year_str = str(year)

        # Check if folder exists
        try:
            results = self.drive_service.files().list(
                q=f"name='{year_str}' and '{self.root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)"
            ).execute()

            if results.get('files'):
                folder_id = results['files'][0]['id']
                self._year_folders[year] = folder_id
                console.print(f"[dim]Using existing folder: {year_str}[/dim]")
                return folder_id
        except HttpError:
            pass

        # Create new folder
        folder_metadata = {
            'name': year_str,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.root_folder_id]
        }

        folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()

        folder_id = folder['id']
        self._year_folders[year] = folder_id
        console.print(f"[cyan]Created folder: {year_str}[/cyan]")

        return folder_id

    def _get_or_create_images_folder(self, year: int) -> str:
        """Get or create the images folder for a given year."""
        if year in self._images_folders:
            return self._images_folders[year]

        year_folder_id = self._get_or_create_year_folder(year)

        # Check if images folder exists
        try:
            results = self.drive_service.files().list(
                q=f"name='images' and '{year_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)"
            ).execute()

            if results.get('files'):
                folder_id = results['files'][0]['id']
                self._images_folders[year] = folder_id
                return folder_id
        except HttpError:
            pass

        # Create new images folder
        folder_metadata = {
            'name': 'images',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [year_folder_id]
        }

        folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()

        folder_id = folder['id']
        self._images_folders[year] = folder_id
        console.print(f"[dim]Created images folder for {year}[/dim]")

        return folder_id

    def _get_root_images_folder(self) -> str:
        """Get or create the root images folder."""
        if self._root_images_folder:
            return self._root_images_folder

        # Check if folder exists
        try:
            results = self.drive_service.files().list(
                q=f"name='images' and '{self.root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)"
            ).execute()

            if results.get('files'):
                self._root_images_folder = results['files'][0]['id']
                return self._root_images_folder
        except HttpError:
            pass

        # Create new folder
        folder_metadata = {
            'name': 'images',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.root_folder_id]
        }

        folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()

        self._root_images_folder = folder['id']
        console.print("[cyan]Created root images folder[/cyan]")

        return self._root_images_folder

    def _upload_image(self, image_path: str, filename: str, year: int) -> Optional[str]:
        """Upload an image to Google Drive."""
        images_folder = self._get_or_create_images_folder(year)

        # Check if file already exists
        try:
            results = self.drive_service.files().list(
                q=f"name='{filename}' and '{images_folder}' in parents",
                fields="files(id)"
            ).execute()

            if results.get('files'):
                return results['files'][0]['id']
        except HttpError:
            pass

        # Upload new file
        file_metadata = {
            'name': filename,
            'parents': [images_folder]
        }

        media = MediaFileUpload(image_path, resumable=True)

        try:
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            console.print(f"  [dim]Uploaded: {filename}[/dim]")
            return file['id']
        except HttpError as e:
            console.print(f"[red]Failed to upload {filename}: {e}[/red]")
            return None

    def _create_document_content(self, parsed_doc: ParsedDocument, year: int) -> List[dict]:
        """
        Create Google Docs document structure from parsed DOCX.

        Returns list of batch update requests.
        """
        requests = []

        # Start with document title
        content_lines = [parsed_doc.title, ""]

        # Add entries
        for entry in parsed_doc.entries:
            # Date header
            content_lines.append(entry.date_display)
            content_lines.append("")

            # Entry content
            if entry.content:
                # Split content into paragraphs
                paragraphs = entry.content.split('\n\n')
                for para in paragraphs:
                    content_lines.append(para.strip())
                    content_lines.append("")

            # Image references
            if entry.images:
                for img_path in entry.images:
                    # Extract filename from path
                    filename = Path(img_path).name
                    # Remove the source prefix to get original filename
                    # e.g., "source_0001.jpg" from "july-1983_source_0001.jpg"
                    if '_' in filename:
                        parts = filename.split('_', 1)
                        if len(parts) > 1:
                            filename = parts[1]

                    content_lines.append(f"[[image: {filename}]]")
                    content_lines.append("")

            # Separator between entries
            content_lines.append("---")
            content_lines.append("")

        # Build insert text requests
        # Google Docs API requires us to insert text, then apply formatting
        # For simplicity, we'll insert everything as plain text first

        # Find the end index after each insertion
        # Start with empty document, index starts at 1
        current_index = 1

        # Split content into segments and create insert requests
        for line in content_lines:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': line + '\n'
                }
            })
            current_index += len(line) + 1

        return requests

    def migrate_document(
        self,
        parsed_doc: ParsedDocument,
        year: int,
        dry_run: bool = False
    ) -> bool:
        """
        Migrate a single parsed document to Google Docs.

        Args:
            parsed_doc: ParsedDocument from parse_docx.py
            year: Year for this document
            dry_run: If True, don't actually create docs

        Returns:
            True if successful
        """
        doc_title = parsed_doc.source_file.replace('.docx', '')
        console.print(f"\n[bold cyan]Migrating:[/bold cyan] {doc_title}")

        if dry_run:
            console.print(f"  [dim]Would create document: {doc_title}[/dim]")
            console.print(f"  [dim]Entries: {len(parsed_doc.entries)}[/dim]")
            return True

        try:
            # Get year folder
            year_folder = self._get_or_create_year_folder(year)

            # Check if document already exists
            doc_id = None
            try:
                results = self.drive_service.files().list(
                    q=f"name='{doc_title}' and '{year_folder}' in parents and mimeType='application/vnd.google-apps.document'",
                    fields="files(id)"
                ).execute()

                if results.get('files'):
                    doc_id = results['files'][0]['id']
                    console.print(f"  [yellow]Document exists, skipping: {doc_title}[/yellow]")
                    return True
            except HttpError:
                pass

            # Create new document directly in the folder using Drive API
            if not doc_id:
                # Create a blank Google Doc in the target folder
                doc_metadata = {
                    'name': doc_title,
                    'mimeType': 'application/vnd.google-apps.document',
                    'parents': [year_folder]
                }
                doc = self.drive_service.files().create(
                    body=doc_metadata,
                    fields='id'
                ).execute()
                doc_id = doc['id']
                console.print(f"  [green]Created document: {doc_title}[/green]")

            # Create content
            requests = self._create_document_content(parsed_doc, year)

            # Apply updates in batches (API has a limit)
            for i in range(0, len(requests), BATCH_LIMIT):
                batch = requests[i:i + BATCH_LIMIT]
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': batch}
                ).execute()

            console.print(f"  [green]✓ Migrated {len(parsed_doc.entries)} entries[/green]")
            return True

        except HttpError as e:
            console.print(f"[red]Error migrating {doc_title}: {e}[/red]")
            return False

    def migrate_all(
        self,
        docs_dir: Path,
        dry_run: bool = False,
        year: Optional[int] = None
    ) -> dict:
        """
        Migrate all DOCX files to Google Docs.

        Args:
            docs_dir: Directory containing DOCX files
            dry_run: If True, don't actually create docs
            year: Default year for abbreviated dates

        Returns:
            Summary dict with counts
        """
        docx_files = find_docx_files(docs_dir)

        if not docx_files:
            console.print("[yellow]No DOCX files found[/yellow]")
            return {'total': 0, 'success': 0, 'failed': 0}

        console.print(f"[bold]Found {len(docx_files)} DOCX file(s)[/bold]")

        summary = {'total': len(docx_files), 'success': 0, 'failed': 0}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Migrating documents...", total=len(docx_files))

            for docx_file in docx_files:
                parsed = parse_docx_file(docx_file, Path.cwd(), year)

                # Determine year from first entry
                doc_year = year
                if parsed.entries:
                    from datetime import datetime
                    try:
                        doc_year = datetime.fromisoformat(parsed.entries[0].date).year
                    except:
                        doc_year = year or datetime.now().year

                if self.migrate_document(parsed, doc_year, dry_run):
                    summary['success'] += 1
                else:
                    summary['failed'] += 1

                progress.update(task, advance=1)

        return summary


# Need to import MediaFileUpload for image uploads
try:
    from googleapiclient.http import MediaFileUpload
except ImportError:
    MediaFileUpload = None
    console.print("[yellow]Warning: MediaFileUpload not available, image upload disabled[/yellow]")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate journal from DOCX to Google Docs"
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        help="Use OAuth (your personal Google account) instead of service account"
    )
    parser.add_argument(
        "--credentials", "-c",
        type=str,
        default="credentials.json",
        help="Path to service account credentials JSON (only used if not --oauth)"
    )
    parser.add_argument(
        "--folder-id", "-f",
        type=str,
        required=True,
        help="Root Google Drive folder ID for journal"
    )
    parser.add_argument(
        "--docs-dir", "-i",
        type=Path,
        default=Path("docs"),
        help="Directory containing DOCX files (default: docs/)"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        default=None,
        help="Default year for abbreviated dates"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without actually creating docs"
    )

    args = parser.parse_args()

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No documents will be created[/yellow]")

    # Create migrator
    if args.oauth:
        migrator = GDocsMigrator(
            root_folder_id=args.folder_id,
            use_oauth=True
        )
    else:
        # Check credentials
        if not Path(args.credentials).exists():
            console.print(f"[red]Credentials file not found: {args.credentials}[/red]")
            return 1
        migrator = GDocsMigrator(
            credentials_path=args.credentials,
            root_folder_id=args.folder_id,
            use_oauth=False
        )

    # Run migration
    summary = migrator.migrate_all(
        docs_dir=args.docs_dir,
        dry_run=args.dry_run,
        year=args.year
    )

    # Print summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Migration Summary[/bold]\n")

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total files", str(summary['total']))
    table.add_row("Successful", str(summary['success']))
    table.add_row("Failed", str(summary['failed']))

    console.print(table)

    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    exit(main())
