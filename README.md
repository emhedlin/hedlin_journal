
A static website generator for family journals. Built from **Google Docs** or Microsoft Word (DOCX) files. Features an interactive timeline, search capabilities, and PDF export.

## Features

- **Google Docs Integration** - Collaborative editing in the browser
- **DOCX Import** - Parse journal entries from Word documents (legacy support)
- **Interactive Timeline** - Canvas-based timeline with hover previews
- **Semantic Search** - Powered by sentence-transformers embeddings
- **PDF Export** - Generate print-ready books (6" × 9" format)
- **Classic Design** - Elegant typography matching traditional journals
- **Static Site** - Fast, secure, easy to deploy

## Quick Start

```bash
# Install dependencies (requires uv)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Configure Google Docs folder ID in config.toml
# Then build the site

# Development build (fast - skips PDFs and embeddings)
python scripts/build_all.py --dev

# Full build (includes PDFs and embeddings)
python scripts/build_all.py

# Start development server
python scripts/serve.py

# Open http://localhost:8000 in your browser
```

## Project Structure

```
hedlin_journal/
├── config.toml            # Configuration (source mode, folder IDs)
├── docs/                  # Legacy: Source DOCX files
│   └── *.docx
├── content/               # Generated Markdown (gitignored)
│   ├── YYYY/MM/
│   └── images/
├── data/                  # Build data (gitignored)
│   ├── build_state.json   # DOCX build state
│   ├── gdocs_state.json   # Google Docs state
│   └── journal_entries.json
├── output/                # Generated website (gitignored)
│   ├── index.html
│   ├── timeline.html
│   ├── archive.html
│   ├── entries/
│   └── static/
├── scripts/               # Build scripts
│   ├── build_all.py       # Main build pipeline
│   ├── fetch_from_gdocs.py # Google Docs → JSON
│   ├── migrate_to_gdocs.py # DOCX → Google Docs migration
│   ├── build.py           # DOCX → JSON → Markdown
│   ├── parse_docx.py      # DOCX parser
│   ├── generate_html.py   # Markdown → HTML
│   ├── generate_embeddings.py  # Generate embeddings
│   ├── generate_pdf.py    # Generate PDFs
│   └── serve.py           # Dev server
├── templates/             # Jinja2 templates
├── static/                # CSS, JS
└── requirements.txt       # Python dependencies
```

## Usage

### Google Docs (Recommended)

The journal can be built from Google Docs, enabling collaborative editing by family members.

**Setup:**
1. Create a Google Drive folder for your journal
2. Create year folders (1983, 1984, etc.)
3. Create a Google Doc for each time period (e.g., "1983-entries")
4. Add the folder ID to `config.toml` under `[gdocs].folder_id`

**Adding/Editing Entries:**
- Open the Google Doc in your browser
- Add or edit entries directly
- Images: Upload to the year's `images/` folder, use `[[image: filename.jpg]]` tag
- Changes are saved automatically in Google Docs
- Rebuild when ready: `python scripts/build_all.py`

**Image Tag Examples:**
```
[[image: beach-day.jpg]]

[[image: family.jpg, caption: Summer 1983]]

[[image: panorama.jpg, width: 600px]]
```

**Migration from DOCX:**
```bash
# Migrate existing DOCX files to Google Docs (uses OAuth)
python scripts/migrate_to_gdocs.py --oauth --folder-id YOUR_FOLDER_ID
```

### DOCX Files (Legacy)

You can still use DOCX files as the source:

**Option 1: Add a new DOCX file**
```bash
# Place your new DOCX file in docs/
cp my_new_entries.docx docs/

# Build from DOCX source
python scripts/build_all.py --source docx
```

**Option 2: Update an existing DOCX file**
```bash
# Edit the DOCX file in place, then rebuild
python scripts/build_all.py --source docx
```

### Build Commands

```bash
# Build from configured source (Google Docs or DOCX)
python scripts/build_all.py

# Specify source explicitly
python scripts/build_all.py --source gdocs   # Google Docs
python scripts/build_all.py --source docx    # DOCX files

# Development build (skip PDFs and embeddings - much faster)
python scripts/build_all.py --dev

# Force rebuild of all files
python scripts/build_all.py --force

# Specify default year for abbreviated dates (DOCX only)
python scripts/build_all.py --year 1983
```

### Deployment

**Build and preview:**
```bash
# Build from Google Docs
python scripts/build_all.py

# Preview locally
python scripts/serve.py
```

**Deploy to GitHub Pages:**
```bash
# Commit the generated output
git add output/
git commit -m "Update journal"
git push
```

## DOCX Format

When using DOCX files, the parser recognizes date headers in these formats:
- `Saturday, July 23, 1983` (full date)
- `Sunday, July 24` (abbreviated, year inferred from context)

Entries should be formatted with date headers followed by content. Images embedded in DOCX files will be extracted automatically.

## Output Formats

| Format | Location | Description |
|--------|----------|-------------|
| HTML | `output/` | Complete static website |
| Markdown | `content/` | Git-friendly source files |
| PDF | `output/hedlin_journal.pdf` | Print-ready book |
| JSON | `data/journal_entries.json` | Structured entry data |
| Embeddings | `output/static/js/embeddings.json` | Timeline/search data |

## Configuration

Edit `config.toml` to configure:

```toml
[source]
# Source mode: "gdocs" (Google Docs) or "docx" (DOCX files)
mode = "gdocs"

[gdocs]
# Google Drive folder ID containing journal documents
folder_id = "your-folder-id-here"
credentials = "credentials.json"

[theme]
# Color palette
background = "#f5f5f5"
text = "#131313"

[site]
title = "Some Same"
```

