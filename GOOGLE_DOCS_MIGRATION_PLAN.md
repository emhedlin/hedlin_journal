# Google Docs Migration Plan

## Overview

Migrate the journal from DOCX files to Google Docs as the source of truth, enabling collaborative editing by family members.

**Current Pipeline:**
```
DOCX files → parse_docx.py → JSON → Markdown → HTML → Website
```

**New Pipeline:**
```
Google Docs → fetch_from_gdocs.py → JSON → Markdown → HTML → Website
                   ↑                              ↓
           (authors & readers edit here)    [Manual deploy to GitHub Pages]

**Build & Deploy Workflow:**
1. Authors edit entries in Google Drive (web UI)
2. You run locally: `python scripts/build_all.py --source gdocs`
3. Preview locally: `python scripts/serve.py`
4. Deploy when ready: `git add output/ && git push`
```

---

## Architecture

### Google Drive Folder Structure

```
Hedlin Family Journal (Google Drive folder)
├── 1983/
│   ├── July 1983             (Google Doc)
│   ├── images/               (Images for July 1983 entries)
│   │   ├── beach-day.jpg
│   │   ├── sandcastle.jpg
│   │   └── ...
│   ├── August 1983           (Google Doc)
│   └── images/
├── 1984/
│   ├── January 1984          (Google Doc)
│   └── images/
└── images/                   (Shared images used across months)
    └── family-portrait.jpg
```

**Design Decision:** One Google Doc per month. This balances:
- Not too many documents (vs. one per entry)
- Not too large (vs. one per year)
- Natural organization matching existing `content/YYYY/MM/` structure

**Image storage:** Separate files in Drive, referenced via tag syntax in docs.

---

### Document Format

Each monthly Google Doc contains entries formatted like:

```
Hedlin Family Journal - July 1983

Saturday, July 23, 1983

We went to the beach today. The weather was perfect!

[[image: beach-day.jpg]]

The kids built a sandcastle and we had ice cream.

[[image: sandcastle.jpg, caption: Ethan and Sophie's masterpiece]]

A great day was had by all.

---

Sunday, July 24

Today we stayed home and rested.

---

Monday, July 25, 1984
[New year detected, year rolls over]
```

**Key conventions:**
- Document title: `{Month} {Year}` (e.g., "July 1983")
- Date headers use existing date patterns (already supported by parser)
- Images referenced via `[[image: filename.jpg]]` tag syntax
- Blank lines between entries for clarity

---

### Image Tag Syntax

```
[[image: filename.jpg]]

[[image: filename.jpg, caption: Optional caption text]]

[[image: filename.jpg, width: 500px]]

[[image: filename.jpg, caption: Caption here, width: 400px]]
```

**Rules:**
- Filename is required
- Options are comma-separated, optional
- `caption` becomes alt text and optional caption below image
- `width` sets image width in pixels

**Image resolution order:**
1. Look in `{month_doc}/images/` folder
2. Look in root `images/` folder (shared images)
3. If not found, leave tag as-is for manual fixing

**Saved filename format:**
```
{month_doc}_{original_filename}
```
Example: `beach-day.jpg` from "July 1983" becomes `1983-07_beach-day.jpg`

This prevents conflicts if the same filename exists in multiple months.

---

## Implementation Phases

### Phase 1: Google Cloud Setup

**Tasks:**
1. Create Google Cloud Project
2. Enable APIs:
   - Google Docs API
   - Google Drive API
3. Create Service Account
4. Share journal folder with Service Account (Editor role)
5. Download credentials JSON

**Deliverable:** `credentials.json` stored securely (not in repo)

---

### Phase 2: Core Parser - fetch_from_gdocs.py

**Purpose:** Replace `parse_docx.py` with Google Docs API version

**Key Functions:**

```python
# Main structure
class GoogleDocsParser:
    def __init__(self, folder_id, credentials_path):
        # Initialize Docs and Drive API clients

    def fetch_all_docs(self):
        # List all docs in the shared folder
        # Return list of (doc_id, title, modified_time)

    def fetch_document_content(self, doc_id):
        # Get document structure from Docs API
        # Extract text and formatting
        # Return structured content

    def parse_entries(self, content):
        # Reuse existing date pattern logic
        # Convert Google Docs rich text to markdown
        # Resolve [[image: ...]] tags
        # Handle year inference

    def resolve_image_tags(self, content, doc_id):
        # Find [[image: ...]] tags
        # Look up images in Drive folders
        # Download if not cached
        # Replace with markdown image syntax

    def build_json(self, all_docs):
        # Combine all entries
        # Sort by date
        # Output same JSON structure as parse_docx.py
```

**Compatibility Requirement:**
- Must output **identical JSON structure** as `parse_docx.py`
- This ensures no changes needed to downstream scripts

---

### Phase 3: Image Handling

**Image Resolution Flow:**
```
Reader sees:   [[image: beach-day.jpg]]
                  ↓
Parser finds:  Drive ID for beach-day.jpg in month folder or root
                  ↓
Downloads:     beach-day.jpg → content/images/1983-07_beach-day.jpg
                  ↓
Markdown:      ![caption](/content/images/1983-07_beach-day.jpg)
                  ↓
HTML:          <img src="/content/images/1983-07_beach-day.jpg" alt="caption">
```

**Parser Logic:**

```python
def resolve_image_tags(content, doc_id, doc_title):
    """
    Find [[image: ...]] tags and replace with markdown image syntax
    """
    image_pattern = re.compile(
        r'\[\[image:\s*([^,\]]+)(?:,\s*(.+?))?\]\]'
    )

    def replace_tag(match):
        filename = match.group(1).strip()
        options_str = match.group(2) or ""

        # Parse options
        caption = extract_option(options_str, "caption")
        width = extract_option(options_str, "width")

        # Find image in Drive (month folder, then shared folder)
        image_id = find_image_in_drive(filename, doc_id)

        if image_id:
            # Download if not cached
            local_path = download_image(
                image_id,
                filename,
                doc_title  # e.g., "July 1983" → "1983-07"
            )
            # Return markdown
            alt = caption or filename
            return f"![{alt}]({local_path})"
        else:
            # Image not found - leave tag as-is for manual fixing
            return match.group(0)

    return image_pattern.sub(replace_tag, content)


def find_image_in_drive(filename, doc_id):
    """
    Search for image file in Drive:
    1. Check month-specific images folder
    2. Check root images folder
    3. Return file ID if found, None otherwise
    """
    month_folder = get_images_folder_for_doc(doc_id)
    shared_folder = get_root_images_folder()

    # Search in month folder
    result = drive_service.files().list(
        q=f"name='{filename}' and '{month_folder}' in parents",
        spaces='drive',
        fields='files(id)'
    ).execute()

    if result.get('files'):
        return result['files'][0]['id']

    # Search in shared folder
    result = drive_service.files().list(
        q=f"name='{filename}' and '{shared_folder}' in parents",
        spaces='drive',
        fields='files(id)'
    ).execute()

    if result.get('files'):
        return result['files'][0]['id']

    return None


def download_image(image_id, filename, doc_title):
    """
    Download image from Drive, save to content/images/
    Returns local path for markdown reference
    """
    # Create safe filename: "1983-07_beach-day.jpg"
    safe_doc_title = doc_title.lower().replace(' ', '-')
    local_filename = f"{safe_doc_title}_{filename}"
    local_path = f"content/images/{local_filename}"

    # Check cache
    if os.path.exists(local_path):
        return f"/{local_path}"

    # Download from Drive
    request = drive_service.files().get_media(fileId=image_id)
    with open(local_path, 'wb') as f:
        f.write(request.execute())

    return f"/{local_path}"
```

**Caching:**
- Images are cached in `content/images/`
- Only re-download if missing
- Prevents unnecessary API calls

---

### Phase 4: Hybrid Image Support

**During migration and transition, support both:**

1. **New format:** `[[image: filename.jpg]]` tags
2. **Legacy format:** Inline images embedded in Google Docs

**Parser handles both:**
- First, resolve `[[image: ...]]` tags
- Then, extract any remaining inline images via Docs API
- This allows gradual migration to the new syntax

**Benefits:**
- No need to immediately convert all existing entries
- Can adopt new syntax for new content
- Old entries continue to work

---

### Phase 5: Incremental Build Support

**Goal:** Only reprocess modified documents (like current build system)

**Strategy:**
1. Store document state in `data/gdocs_state.json`:
   ```json
   {
     "last_checked": "2024-01-15T10:30:00Z",
     "documents": {
       "1983-07": {
         "doc_id": "abc123",
         "title": "July 1983",
         "modified_time": "2024-01-15T10:30:00Z",
         "checksum": "sha256..."
       }
     }
   }
   ```

2. On each build:
   - Fetch folder listing with `modifiedTime`
   - Compare against stored state
   - Only fetch and parse changed documents

3. Image tracking:
   - Track downloaded images by hash
   - Re-download only if file changed

**Benefit:** Fast builds even with many entries

---

### Phase 6: Migration - DOCX to Google Docs

**Initial Setup (One-time):**

**Semi-Manual Approach (Recommended):**

1. **Create Google Drive folder structure:**
   - Create main "Hedlin Family Journal" folder
   - Create year folders (1983, 1984, etc.)
   - Create an images/ folder at root

2. **Run migration script:**
   ```python
   # scripts/migrate_to_gdocs.py
   for docx_file in docs/:
       # Extract entries using parse_docx.py
       # Create Google Doc via API
       # Format with date headers
       # Extract and upload images to month folders
       # Replace inline images with [[image: ...]] tags
       # Place doc in appropriate year folder
   ```

3. **Review and organize:**
   - Check in Google Drive UI
   - Verify images uploaded correctly
   - Fix any formatting issues
   - Share with collaborators

**Why Semi-Manual?**
- Gives you control over initial organization
- Can verify content during migration
- Opportunity to clean up/format as you go
- Visual confirmation in Drive UI

---

### Phase 7: Integration with Build Pipeline

**Modify `scripts/build_all.py`:**

```python
# Add flag to choose source
parser = args.source if args.source else config.get('source', 'docx')

if parser == 'gdocs':
    from fetch_from_gdocs import GoogleDocsParser
    entries = GoogleDocsParser(config.gdocs_folder).parse()
else:
    from parse_docx import DocxParser  # Fallback to DOCX
    entries = DocxParser(config.docs_path).parse()
```

**Config.toml addition:**
```toml
[source]
mode = "docx"  # or "gdocs"

[gdocs]
folder_id = "your-google-drive-folder-id"
credentials = "credentials.json"
```

---

### Phase 8: Local Build & Deploy

**Build Commands:**

```bash
# Build from Google Docs
python scripts/build_all.py --source gdocs

# Preview locally (before deploying)
python scripts/serve.py
# Opens at http://localhost:8000

# Deploy to GitHub Pages (when ready)
git add output/ && git commit -m "Update journal from Google Docs" && git push
```

**GitHub Pages Setup (One-time):**

1. Go to repo Settings → Pages
2. Source: Deploy from a branch
3. Branch: `main` / `/output`
4. Save

GitHub will now automatically serve the `output/` directory as your website.

**Credentials:**

Store `credentials.json` locally at project root. **Add to `.gitignore`:**

```bash
# .gitignore
credentials.json
```

Credentials never leave your machine. Simple and secure.

---

### Phase 9: Quick Reference Card

**Your day-to-day workflow:**
```bash
# After family makes changes, rebuild and deploy
python scripts/build_all.py --source gdocs
python scripts/serve.py  # Preview
git add output/ && git push  # Deploy
```

---

### Phase 10: Workflow & Documentation

**For Contributors (Non-Technical):**

1. **Access:**
   - Share Google Drive folder with family members (Viewer or Editor)
   - For editors: share with "Editor" permission
   - For viewers: share with "Viewer" permission

2. **Finding Entries:**
   - Navigate to Year folder
   - Open month document
   - Scroll to date or use Ctrl+F to search

3. **Editing Entries:**
   - Open the document
   - Make changes directly
   - For images: upload to month's images folder, add `[[image: filename]]` tag
   - Save (automatic in Google Docs)

4. **Publishing:**
   - Changes appear after next weekly build
   - Or trigger manual build via GitHub Actions UI

**Image Management for Contributors:**

1. **Adding an image:**
   - Upload image file to the month's `images/` folder
   - In the document, add `[[image: your-photo.jpg]]` where desired

2. **Replacing an image:**
   - Upload new file with same name
   - It will be used on next build

3. **Deleting an image:**
   - Remove `[[image: ...]]` tag from document
   - Optionally delete file from Drive

**For Maintainer (You):**

1. **When family says they've made changes:**
   ```bash
   python scripts/build_all.py --source gdocs
   ```

2. **Preview before deploying:**
   ```bash
   python scripts/serve.py  # Opens http://localhost:8000
   ```

3. **Deploy to GitHub Pages:**
   ```bash
   git add output/
   git commit -m "Update journal from Google Docs"
   git push
   ```

4. **Review what changed:**
   - Check `data/gdocs_state.json` for what was processed
   - Check `git diff output/` for what changed

---

## Technical Considerations

### Rate Limits

- Google Docs API: Free tier is generous for personal use
- Drive API: No practical issues for personal journal volume

**Mitigation:**
- Incremental builds minimize API calls (only fetch changed docs)
- Images cached locally in `content/images/`
- You control when builds happen (no automated polling)

---

### Storage & Git Strategy

**Single source of truth:** Google Drive is the source; git is for code only.

```
In Git (committed):
├── scripts/           (Build scripts)
├── templates/         (HTML templates)
├── static/            (CSS, JS)
├── config.toml        (Configuration)
└── .gitignore         (Excludes generated content)

NOT in Git (gitignored):
├── credentials.json   (Google service account)
├── content/images/    (Downloaded from Drive - build cache)
├── data/              (Build state, regenerated)
└── output/            (Generated site - deployed via GitHub Actions)
```

**Why images are NOT in git:**
1. **Single source of truth** = Google Drive (where images are edited)
2. **Repo stays small** = easier to clone and manage
3. **`content/images/` is a build cache** = like `node_modules/` or similar
4. **Images end up in `output/`** = which gets deployed to GitHub Pages

**First clone setup:**
```bash
git clone <repo>
python scripts/build_all.py --source gdocs
# Downloads all images from Drive to content/images/
```

**Subsequent builds (incremental):**
```bash
python scripts/build_all.py --source gdocs
# Only downloads new/changed images (checks cache)
```

**.gitignore entries:**
```gitignore
# Google Docs credentials (never commit)
credentials.json

# Build cache (regenerated from Google Drive)
content/images/
data/

# Generated site (deployed via GitHub Actions)
output/
```

### Markdown Conversion

Google Docs uses rich text structure. Need conversion:

| Google Docs Element | Markdown Output |
|---------------------|-----------------|
| Bold (`textStyle.bold`) | `**text**` |
| Italic (`textStyle.italic`) | `*text*` |
| Link (`textStyle.link`) | `[text](url)` |
| Paragraph | Blank line between |
| Heading | `# Heading` (if used) |

**Implementation:**
```python
def element_to_markdown(element):
    # Recursively convert Google Docs structural elements to markdown
    # Handle text runs with formatting
    # Preserve line breaks and paragraphs
    # Process [[image: ...]] tags
```

### Version History

Google Docs automatically maintains version history. This is a **benefit**:
- No need to version control source files
- Can revert changes easily
- See who changed what
- Built-in collaboration conflict resolution

---

## Rollout Strategy

### Step 1: Folder Setup (Day 1)
- Create Google Drive folder structure
- Set up year folders
- Create images folders

### Step 2: Migration Script Run (Day 2)
- Run migration script
- Verify content transferred correctly
- Check images uploaded properly

### Step 3: Manual Review (Day 3-7)
- Spot-check entries in Google Drive UI
- Fix any formatting issues
- Clean up image tags if needed

### Step 4: Parallel Run (Week 2)
- Keep existing DOCX pipeline active
- Build Google Docs version locally
- Compare outputs to verify parity

### Step 5: Soft Launch (Week 3)
- Switch `config.toml` to use `gdocs` source
- Add 1-2 trusted contributors
- Monitor for issues

### Step 6: Full Rollout (Week 4+)
- Onboard all contributors
- Keep DOCX as backup/archive
- Build and deploy on your schedule

### Fallback
- Keep DOCX files archived forever
- Can revert by changing `config.toml` to `mode = "docx"`

---

## Dependencies

**New Python packages required:**
```txt
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=0.5.0
```

Add to `requirements.txt`:
```
google-api-python-client==2.100.0
google-auth==2.23.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
```

---

## Success Criteria

**Setup:**
- [ ] Google Cloud project created with APIs enabled
- [ ] Service account credentials stored locally (gitignored)
- [ ] Google Drive folder shared with service account

**Functionality:**
- [ ] Can fetch all documents from Google Drive
- [ ] Output JSON matches `parse_docx.py` structure exactly
- [ ] `[[image: ...]]` tags resolve correctly
- [ ] Images download and display with correct paths
- [ ] Hybrid support works (embedded + tagged images)
- [ ] Incremental builds work (only fetch changed docs)
- [ ] Local preview works with `scripts/serve.py`

**People:**
- [ ] Non-technical users can edit entries successfully
- [ ] Documentation exists for contributors

**Deployment:**
- [ ] GitHub Pages configured to serve `output/` directory
- [ ] Deploy workflow tested (git push updates site)
- [ ] Fallback to DOCX source works via `config.toml`
