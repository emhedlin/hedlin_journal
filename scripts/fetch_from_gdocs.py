#!/usr/bin/env python3
"""
Fetch and parse journal entries from Google Docs.

This script extracts:
- Title/intro section
- Journal entries with dates
- Images referenced via [[image: ...]] tags or embedded in docs
- Converts to structured JSON format compatible with the build pipeline

Replaces parse_docx.py for Google Docs source.
"""

import argparse
import base64
import json
import hashlib
import io
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PIL import Image
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


# Date patterns to recognize journal entry dates (same as parse_docx.py)
DATE_PATTERNS = [
    # Day of week + Month + Day + Year
    re.compile(
        r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2}),?\s+(\d{4})',
        re.IGNORECASE
    ),
    # Day of week + Month + Day (no year)
    re.compile(
        r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2})\b',
        re.IGNORECASE
    ),
    # Just Month + Day + Year
    re.compile(
        r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2}),?\s+(\d{4})',
        re.IGNORECASE
    ),
]

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

# Image tag pattern: [[image: filename.jpg]] or [[image: filename.jpg, caption: text]]
IMAGE_TAG_PATTERN = re.compile(
    r'\[\[image:\s*([^,\]]+)(?:,\s*(.+?))?\]\]',
    re.IGNORECASE
)


@dataclass
class JournalEntry:
    """A single journal entry."""
    date: str  # ISO date string (YYYY-MM-DD)
    date_display: str  # Original date text from document
    title: Optional[str] = None  # Optional title
    content: str = ""  # Entry content as markdown
    images: List[str] = None  # List of image filenames
    source_file: str = ""  # Source document name
    source_index: int = -1  # Paragraph index in source

    def __post_init__(self):
        if self.images is None:
            self.images = []


@dataclass
class ParsedDocument:
    """A parsed Google Doc containing journal entries."""
    title: str
    intro: str
    entries: List[JournalEntry]
    source_file: str
    parsed_at: str


def extract_date_from_text(text: str) -> tuple[Optional[datetime], Optional[str]]:
    """
    Extract a date from the given text.

    Returns (datetime, display_text) or (None, display_text) for abbreviated dates.
    """
    text = text.strip()

    for pattern in DATE_PATTERNS:
        match = pattern.match(text)
        if match:
            groups = match.groups()

            if len(groups) == 4:  # Full date with day, month, day, year
                day_name, month_name, day_num, year = groups
                month = MONTH_MAP[month_name.lower()]
                try:
                    date_obj = datetime(int(year), month, int(day_num))
                    return date_obj, match.group(0)
                except ValueError:
                    continue

            elif len(groups) == 3:
                # Could be (day, month, day) abbreviated, or (month, day, year)
                if groups[0] in MONTH_MAP:  # (month, day, year)
                    month_name, day_num, year = groups
                    month = MONTH_MAP[month_name.lower()]
                    try:
                        date_obj = datetime(int(year), month, int(day_num))
                        return date_obj, match.group(0)
                    except ValueError:
                        continue
                else:  # (day, month, day) - abbreviated, no year
                    # Return None for date to indicate we need context
                    return None, match.group(0)

    return None, None


def get_file_hash(content: bytes) -> str:
    """Generate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


class GoogleDocsParser:
    """Parser for Google Docs journal entries."""

    # Scopes required for Docs and Drive API
    SCOPES = [
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
    ]

    def __init__(self, credentials_path: str, folder_id: str, output_dir: Path):
        """
        Initialize the parser.

        Args:
            credentials_path: Path to service account credentials JSON
            folder_id: Google Drive folder ID containing journal docs
            output_dir: Directory for output and cached content
        """
        self.folder_id = folder_id
        self.output_dir = Path(output_dir)
        self.project_root = Path.cwd()

        # Create images directory
        self.images_dir = self.project_root / "content" / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Authenticate and build API clients
        self.docs_service, self.drive_service = self._authenticate(credentials_path)

        # Load build state for incremental builds
        self.state = self._load_state()

        # Cache for folder lookups
        self._folder_cache: Dict[str, str] = {}
        self._root_images_folder: Optional[str] = None

    def _authenticate(self, credentials_path: str):
        """Authenticate with Google APIs using service account."""
        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=self.SCOPES
        )

        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        console.print("[green]Authenticated with Google APIs[/green]")
        return docs_service, drive_service

    def _load_state(self) -> Dict[str, Any]:
        """Load incremental build state from gdocs_state.json."""
        state_file = self.project_root / "data" / "gdocs_state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        return {
            "last_checked": None,
            "documents": {},
            "images": {}
        }

    def _save_state(self):
        """Save incremental build state."""
        state_file = self.project_root / "data"
        state_file.mkdir(parents=True, exist_ok=True)
        state_file = state_file / "gdocs_state.json"

        self.state["last_checked"] = datetime.now().isoformat()

        with open(state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def list_docs(self) -> List[Dict[str, Any]]:
        """
        List all Google Docs in the configured folder and its subfolders.

        Returns list of dicts with: id, title, modified_time
        """
        docs = []

        try:
            # First, get all subfolders (year folders)
            folder_results = self.drive_service.files().list(
                q=f"'{self.folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)",
                pageSize=100
            ).execute()

            folders = [self.folder_id]  # Include root folder
            for folder in folder_results.get('files', []):
                folders.append(folder['id'])

            # Search for documents in each folder
            for folder_id in folders:
                results = self.drive_service.files().list(
                    q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
                    fields="files(id, name, modifiedTime)",
                    pageSize=100
                ).execute()

                items = results.get('files', [])
                for item in items:
                    docs.append({
                        'id': item['id'],
                        'title': item['name'],
                    'modified_time': item['modifiedTime']
                })

            console.print(f"[cyan]Found {len(docs)} document(s)[/cyan]")
            return docs

        except HttpError as error:
            console.print(f"[red]Error listing files: {error}[/red]")
            return []

    def _get_images_folder_id(self, doc_title: str) -> Optional[str]:
        """
        Get the ID of the images folder for a given document.

        Looks for a folder named "images" in the same parent folder as the doc.
        """
        doc_key = f"images_folder_{doc_title}"

        if doc_key in self._folder_cache:
            return self._folder_cache[doc_key]

        try:
            # Get the parent folder of the document
            doc_info = self.drive_service.files().get(
                fileId=self.folder_id,
                fields="parents"
            ).execute()

            if not doc_info.get('parents'):
                return None

            parent_id = doc_info['parents'][0]

            # Look for an images folder in the parent
            results = self.drive_service.files().list(
                q=f"'{parent_id}' in parents and name='images' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)"
            ).execute()

            items = results.get('files', [])
            if items:
                folder_id = items[0]['id']
                self._folder_cache[doc_key] = folder_id
                return folder_id

        except HttpError:
            pass

        return None

    def _get_root_images_folder(self) -> Optional[str]:
        """Get the ID of the root images folder."""
        if self._root_images_folder is not None:
            return self._root_images_folder

        try:
            # Get the parent of the main folder
            folder_info = self.drive_service.files().get(
                fileId=self.folder_id,
                fields="parents"
            ).execute()

            if not folder_info.get('parents'):
                return None

            root_id = folder_info['parents'][0]

            # Look for images folder at root level
            results = self.drive_service.files().list(
                q=f"'{root_id}' in parents and name='images' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)"
            ).execute()

            items = results.get('files', [])
            if items:
                self._root_images_folder = items[0]['id']
                return self._root_images_folder

        except HttpError:
            pass

        return None

    def _find_image_in_drive(self, filename: str, doc_title: str) -> Optional[str]:
        """
        Search for an image file in Google Drive.

        Searches in:
        1. Month-specific images folder (YYYY/images/)
        2. Root images folder

        Returns the file ID if found, None otherwise.
        """
        filename = filename.strip()

        # Try month-specific folder first
        month_folder = self._get_images_folder_id(doc_title)
        if month_folder:
            try:
                result = self.drive_service.files().list(
                    q=f"name='{filename}' and '{month_folder}' in parents",
                    spaces='drive',
                    fields='files(id, name)',
                    pageSize=10
                ).execute()

                if result.get('files'):
                    return result['files'][0]['id']
            except HttpError:
                pass

        # Try root images folder
        root_folder = self._get_root_images_folder()
        if root_folder:
            try:
                result = self.drive_service.files().list(
                    q=f"name='{filename}' and '{root_folder}' in parents",
                    spaces='drive',
                    fields='files(id, name)',
                    pageSize=10
                ).execute()

                if result.get('files'):
                    return result['files'][0]['id']
            except HttpError:
                pass

        return None

    def _download_image(self, image_id: str, filename: str, doc_title: str) -> Optional[str]:
        """
        Download an image from Drive and save locally.

        Returns the relative path to the saved image, or None if failed.
        """
        # Create safe filename from doc title
        safe_doc_title = doc_title.lower().replace(' ', '-')
        local_filename = f"{safe_doc_title}_{filename}"
        local_path = self.images_dir / local_filename

        # Check cache
        if local_path.exists():
            return f"/content/images/{local_filename}"

        try:
            # Download from Drive
            request = self.drive_service.files().get_media(fileId=image_id)
            content = request.execute()

            # Save locally
            with open(local_path, 'wb') as f:
                f.write(content)

            console.print(f"  [dim]Downloaded image: {local_filename}[/dim]")

            # Track in state
            file_hash = get_file_hash(content)
            self.state["images"][local_filename] = {
                "hash": file_hash,
                "source_id": image_id,
                "downloaded_at": datetime.now().isoformat()
            }

            return f"/content/images/{local_filename}"

        except HttpError as e:
            console.print(f"[red]Failed to download image {filename}: {e}[/red]")
            return None

    def _resolve_image_tags(self, content: str, doc_title: str) -> str:
        """
        Resolve [[image: ...]] tags in content.

        Replaces tags with markdown image syntax.
        """
        def replace_tag(match):
            filename = match.group(1).strip()
            options_str = match.group(2) or ""

            # Parse options
            caption = None
            width = None

            if options_str:
                # Parse key: value options
                for option in re.split(r',\s*', options_str):
                    option = option.strip()
                    if ':' in option:
                        key, value = option.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if key == 'caption':
                            caption = value
                        elif key == 'width':
                            width = value

            # Find and download image
            image_id = self._find_image_in_drive(filename, doc_title)

            if image_id:
                local_path = self._download_image(image_id, filename, doc_title)
                if local_path:
                    alt = caption or filename
                    if width:
                        # Markdown doesn't support width natively, use HTML
                        return f'<img src="{local_path}" alt="{alt}" width="{width}">'
                    return f"![{alt}]({local_path})"
                else:
                    # Download failed, leave tag for manual fixing
                    return match.group(0)
            else:
                # Image not found, leave tag for manual fixing
                console.print(f"[yellow]Image not found: {filename}[/yellow]")
                return match.group(0)

        return IMAGE_TAG_PATTERN.sub(replace_tag, content)

    def _element_to_markdown(self, element: Dict[str, Any], doc_id: str, doc_title: str) -> str:
        """
        Convert a Google Docs structural element to markdown.

        Handles text runs with formatting (bold, italic, links).
        """
        if 'paragraph' not in element:
            return ''

        paragraph = element['paragraph']
        if not paragraph.get('elements'):
            return ''

        text_parts = []

        for elem in paragraph['elements']:
            if 'textRun' not in elem:
                continue

            text_run = elem['textRun']
            content = text_run['content']
            text_style = text_run.get('textStyle', {})

            # Handle bold
            if text_style.get('bold'):
                content = f"**{content}**"

            # Handle italic
            if text_style.get('italic'):
                content = f"*{content}*"

            # Handle links
            if text_style.get('link'):
                url = text_style['link'].get('url', '')
                content = content.rstrip()  # Remove trailing newline for links
                content = f"[{content}]({url})"

            text_parts.append(content)

        text = ''.join(text_parts)

        # Check for image tags in this paragraph
        text = self._resolve_image_tags(text, doc_title)

        return text

    def fetch_document(self, doc_id: str, doc_title: str) -> ParsedDocument:
        """
        Fetch and parse a single Google Doc.

        Args:
            doc_id: Google Doc ID
            doc_title: Document title

        Returns:
            ParsedDocument with entries
        """
        console.print(f"\n[bold cyan]Fetching:[/bold cyan] {doc_title}")

        # Check if document needs reprocessing
        doc_key = f"{doc_title}_{doc_id}"
        if doc_key in self.state['documents']:
            stored_time = self.state['documents'][doc_key].get('processed_time')
            # Could check modified_time here for incremental builds
            # For now, always process

        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
        except HttpError as e:
            console.print(f"[red]Error fetching document {doc_title}: {e}[/red]")
            return ParsedDocument(
                title=doc_title,
                intro="",
                entries=[],
                source_file=doc_title,
                parsed_at=datetime.now().isoformat()
            )

        # Extract content
        content = doc.get('body', {}).get('content', [])

        entries = []
        current_entry: Optional[JournalEntry] = None
        current_content: List[str] = []
        intro_lines: List[str] = []
        title = doc_title
        entry_images: List[str] = []

        # Set default year from first full date
        default_year = None
        for element in content:
            text = self._element_to_markdown(element, doc_id, doc_title)
            if not text or not text.strip():
                continue

            date_obj, date_display = extract_date_from_text(text.strip())
            if date_obj and default_year is None:
                default_year = date_obj.year
                console.print(f"[dim]Detected default year: {default_year}[/dim]")
                break

        last_year = default_year or datetime.now().year

        # Process document content
        for element in content:
            text = self._element_to_markdown(element, doc_id, doc_title)

            if not text or not text.strip():
                continue

            text = text.strip()

            # Check if this is a date header
            date_obj, date_display = extract_date_from_text(text)

            if date_display:
                # Save previous entry
                if current_entry:
                    current_entry.content = '\n\n'.join(current_content)
                    current_entry.images = entry_images.copy()
                    entries.append(current_entry)

                # Handle abbreviated dates (no year)
                if date_obj:
                    entry_date = date_obj
                    last_year = entry_date.year
                else:
                    # Parse the abbreviated date
                    month_match = re.search(
                        r'(January|February|March|April|May|June|July|August|September|October|November|December)',
                        text,
                        re.IGNORECASE
                    )
                    day_match = re.search(r'\b(\d{1,2})\b', text)

                    if month_match and day_match:
                        month = MONTH_MAP[month_match.group(0).lower()]
                        try:
                            entry_date = datetime(last_year, month, int(day_match.group(0)))
                        except ValueError:
                            entry_date = datetime.now()
                    else:
                        entry_date = datetime.now()

                # Create new entry
                current_entry = JournalEntry(
                    date=entry_date.strftime('%Y-%m-%d'),
                    date_display=date_display,
                    source_file=doc_title,
                    source_index=len(entries)
                )
                current_content = []
                entry_images = []

            elif current_entry:
                # Add content to current entry
                current_content.append(text)

                # Check for embedded images (for hybrid support)
                # This handles images directly embedded in Google Docs
                if 'inlineObjectElement' in str(element):
                    # Extract inline images from Google Docs
                    # For now, we'll handle this in a follow-up
                    pass

            else:
                # Before first entry - collect intro
                if title == doc_title and not any(t.strip() for t in intro_lines):
                    # First non-date line might be the title
                    pass
                intro_lines.append(text)

        # Save last entry
        if current_entry:
            current_entry.content = '\n\n'.join(current_content)
            current_entry.images = entry_images.copy()
            entries.append(current_entry)

        # Build intro
        intro = '\n\n'.join(intro_lines[:10])

        console.print(f"[green]  Found {len(entries)} entries[/green]")

        # Update state
        self.state['documents'][doc_key] = {
            'doc_id': doc_id,
            'title': doc_title,
            'processed_time': datetime.now().isoformat(),
            'entry_count': len(entries)
        }

        return ParsedDocument(
            title=title,
            intro=intro,
            entries=entries,
            source_file=doc_title,
            parsed_at=datetime.now().isoformat()
        )

    def parse_all(self) -> Dict[str, Any]:
        """
        Fetch and parse all documents from Google Drive.

        Returns the combined JSON structure matching parse_docx.py output.
        """
        docs = self.list_docs()

        if not docs:
            console.print("[yellow]No documents found[/yellow]")
            return self._empty_output()

        all_parsed_docs = []
        all_entries = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching documents...", total=len(docs))

            for doc_info in docs:
                parsed = self.fetch_document(
                    doc_info['id'],
                    doc_info['title']
                )
                all_parsed_docs.append(parsed)
                all_entries.extend(parsed.entries)
                progress.update(task, advance=1)

        # Save state
        self._save_state()

        # Build output matching parse_docx.py format
        return self._build_output(all_parsed_docs, all_entries)

    def _empty_output(self) -> Dict[str, Any]:
        """Return empty output structure."""
        return {
            "title": "Hedlin Family Journal",
            "parsed_at": datetime.now().isoformat(),
            "documents": [],
            "entries": []
        }

    def _build_output(
        self,
        parsed_docs: List[ParsedDocument],
        all_entries: List[JournalEntry]
    ) -> Dict[str, Any]:
        """Build the output JSON structure matching parse_docx.py."""
        return {
            "title": "Hedlin Family Journal",
            "parsed_at": datetime.now().isoformat(),
            "documents": [
                {
                    "title": doc.title,
                    "source_file": doc.source_file,
                    "intro": doc.intro,
                    "entry_count": len(doc.entries)
                }
                for doc in parsed_docs
            ],
            "entries": [
                {
                    "date": entry.date,
                    "date_display": entry.date_display,
                    "title": entry.title,
                    "content": entry.content,
                    "images": entry.images,
                    "source_file": entry.source_file
                }
                for entry in sorted(all_entries, key=lambda e: e.date)
            ]
        }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch journal entries from Google Docs"
    )
    parser.add_argument(
        "--credentials", "-c",
        type=str,
        default="credentials.json",
        help="Path to service account credentials JSON (default: credentials.json)"
    )
    parser.add_argument(
        "--folder-id", "-f",
        type=str,
        required=True,
        help="Google Drive folder ID containing journal documents"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("data"),
        help="Directory for output JSON files (default: data/)"
    )

    args = parser.parse_args()

    # Check credentials file exists
    if not Path(args.credentials).exists():
        console.print(f"[red]Credentials file not found: {args.credentials}[/red]")
        console.print("\n[yellow]To set up Google Cloud credentials:[/yellow]")
        console.print("1. Create a Google Cloud Project")
        console.print("2. Enable Docs API and Drive API")
        console.print("3. Create a service account")
        console.print("4. Download credentials JSON")
        console.print("5. Share your Drive folder with the service account email")
        return 1

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Create parser and fetch
    gdocs_parser = GoogleDocsParser(
        credentials_path=args.credentials,
        folder_id=args.folder_id,
        output_dir=args.output
    )

    output_data = gdocs_parser.parse_all()

    # Write output
    output_file = args.output / "journal_entries.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]Output written to:[/green] {output_file}")
    console.print(f"[green]Total entries: {len(output_data['entries'])}[/green]")

    return 0


if __name__ == "__main__":
    exit(main())
