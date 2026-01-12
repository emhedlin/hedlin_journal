#!/usr/bin/env python3
"""
Create a HOW_TO_USE document in the Google Drive journal folder.
"""

import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from rich.console import Console

console = Console()

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]

INSTRUCTIONS_CONTENT = '''# Hedlin Family Journal - How to Use

Welcome! This document explains how to read and contribute to the family journal.


## Reading Entries

1. **Navigate by Year:**
   - Open the "Hedlin Family Journal" folder
   - Open a year folder (e.g., "1983")
   - Open the document for that time period

2. **Find a Specific Date:**
   - Use Ctrl+F (or Cmd+F on Mac) to search within a document
   - Type the date you're looking for
   - Example: "July 23" or "Saturday, July 23"


## Editing Entries

Anyone with access can edit entries:

1. Open the document you want to edit
2. Make your changes directly
   - Fix typos
   - Add missing details
   - Clarify confusing parts
3. **The changes are saved automatically!**

No need to "submit" or "publish" - just edit and it's saved.


## Adding Photos

To add a photo to an entry:

1. **Upload the Image:**
   - Go to the `images` folder in the same year folder
   - Click "New" → "File upload"
   - Select your photo and upload it
   - Remember the filename!

2. **Add the Image Tag:**
   - Open the journal document
   - Find the entry where you want the photo
   - Add the image tag where you want it to appear:

     [[image: your-photo-name.jpg]]

3. **That's it!** The photo will appear when the journal is rebuilt.

**Image Tag Examples:**
```
[[image: beach-day.jpg]]

[[image: family-portrait.jpg, caption: The whole family in 1983]]

[[image: sandcastle.jpg, caption: Ethan's masterpiece]]
```


## Image Tag Options

You can add optional details to your image tag:

- **caption:** Text that describes the photo
- **width:** Size in pixels (for large photos)

Examples:
```
[[image: vacation.jpg, caption: Summer trip to the lake]]

[[image: panorama.jpg, width: 600px]]
```


## Formatting Guidelines

When adding or editing entries, please:

- **Start each entry with the date:**
  - Full format: "Saturday, July 23, 1983"
  - Or: "July 23, 1983"
  - Or just: "Saturday, July 23" (if year is clear)

- **Separate entries with blank lines**

- **Use simple formatting:**
  - Bold: **important text**
  - Italic: *emphasis*
  - Links: [click here](https://example.com)


## Need Help?

If something doesn't work or you have questions:
- Contact Erik
- Or leave a comment in the document using Insert → Comment


---

Happy journaling! 📖
'''


def get_credentials():
    """Get OAuth credentials."""
    token_path = Path.cwd() / "token.json"
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow

            client_secret = Path.cwd() / "client_secret.json"
            if not client_secret.exists():
                raise FileNotFoundError("client_secret.json not found")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds


def create_instructions_doc(folder_id: str):
    """Create the HOW_TO_USE document in Google Drive."""
    console.print("Creating instructions document...")

    creds = get_credentials()
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Create the document in the folder
    doc_metadata = {
        'name': 'HOW_TO_USE',
        'mimeType': 'application/vnd.google-apps.document',
        'parents': [folder_id]
    }

    doc = drive_service.files().create(
        body=doc_metadata,
        fields='id'
    ).execute()

    doc_id = doc['id']
    console.print(f"Created document with ID: {doc_id}")

    # Add content
    # Split content into lines and create insert requests
    requests = []
    index = 1

    for line in INSTRUCTIONS_CONTENT.split('\n'):
        requests.append({
            'insertText': {
                'location': {'index': index},
                'text': line + '\n'
            }
        })
        index += len(line) + 1

    # Apply formatting for headers (lines starting with #)
    # This is a simple version - for full formatting we'd need more complex processing
    batch_size = 100
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': batch}
        ).execute()

    console.print("[green]Instructions document created successfully![/green]")
    console.print(f"Look for 'HOW_TO_USE' in your Hedlin Family Journal folder")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        folder_id = "1az3bUaEal-dHi_vBmzWY8upCl90s4NQu"  # Default folder ID
    else:
        folder_id = sys.argv[1]

    create_instructions_doc(folder_id)
