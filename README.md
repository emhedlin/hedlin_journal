# Hedlin Family Journal

A static website generator for family journals, built from Microsoft Word (DOCX) files. Features an interactive timeline, search capabilities, and PDF export.

## Features

- 📝 **DOCX Import** - Parse journal entries from Word documents
- 📅 **Interactive Timeline** - Canvas-based timeline with hover previews
- 🔍 **Semantic Search** - Powered by sentence-transformers embeddings
- 📄 **PDF Export** - Generate print-ready books (6" × 9" format)
- 🎨 **Classic Design** - Elegant typography matching traditional journals
- 🚀 **Static Site** - Fast, secure, easy to deploy

## Quick Start

```bash
# Install dependencies (requires uv)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Place your DOCX files in the docs/ directory
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
├── docs/                  # Source DOCX files
│   └── *.docx
├── content/               # Generated Markdown (gitignored)
│   ├── YYYY/MM/
│   └── images/
├── data/                  # Build data (gitignored)
│   ├── build_state.json
│   └── journal_entries.json
├── output/                # Generated website (gitignored)
│   ├── index.html
│   ├── timeline.html
│   ├── archive.html
│   ├── entries/
│   └── static/
├── scripts/               # Build scripts
│   ├── build_all.py       # Main build pipeline
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

### Adding New Entries

**Option 1: Add a new DOCX file**
```bash
# Place your new DOCX file in docs/
cp my_new_entries.docx docs/

# Rebuild
python scripts/build_all.py
```

**Option 2: Update an existing DOCX file**
```bash
# Edit the DOCX file in place, then rebuild
python scripts/build_all.py
```

**Option 3: Edit Markdown directly**
```bash
# Markdown files are in content/YYYY/MM/
# Edit them directly and regenerate HTML
python scripts/generate_html.py -c content -o output
```

### Build Commands

```bash
# Full build (everything)
python scripts/build_all.py

# Development build (skip PDFs and embeddings - much faster)
python scripts/build_all.py --dev

# Force rebuild of all files
python scripts/build_all.py --force

# Specify default year for abbreviated dates
python scripts/build_all.py --year 1983

# Skip only PDFs
python scripts/build_all.py --skip-pdf

# Skip only embeddings
python scripts/build_all.py --skip-embeddings
```

### Individual Build Steps

```bash
# Parse DOCX and generate Markdown
python scripts/build.py -i docs -d data -o .

# Generate HTML website only
python scripts/generate_html.py -c content -o output -t templates -s static

# Generate embeddings for timeline
python scripts/generate_embeddings.py -i data/journal_entries.json -o output/static/js/embeddings.json

# Generate PDFs
python scripts/generate_pdf.py -c content -o output -t templates
```

### Development Server

```bash
# Start server (default port 8000)
python scripts/serve.py

# Custom port
python scripts/serve.py --port 3000

# Don't open browser automatically
python scripts/serve.py --no-browser
```

## DOCX Format

The parser recognizes date headers in these formats:
- `Saturday, July 23, 1983` (full date)
- `Sunday, July 24` (abbreviated, year inferred)

Entries should be formatted with date headers followed by content. Images embedded in DOCX files will be extracted automatically.

## Output Formats

| Format | Location | Description |
|--------|----------|-------------|
| HTML | `output/` | Complete static website |
| Markdown | `content/` | Git-friendly source files |
| PDF | `output/hedlin_journal.pdf` | Print-ready book |
| JSON | `data/journal_entries.json` | Structured entry data |
| Embeddings | `output/static/js/embeddings.json` | Timeline/search data |

## Deployment

### GitHub Pages

```bash
# Build the site
python scripts/build_all.py

# The output/ directory is ready to deploy
# Use GitHub Pages with source: output/
```

### Netlify

```bash
# Deploy output/ directory
netlify deploy --prod --dir=output
```

### Any Static Host

The `output/` directory is a self-contained static site. Upload it to any web host.

## Requirements

- Python 3.11+
- uv (recommended) or pip
- Dependencies in `requirements.txt`

## Development

### Adding New Features

The codebase is organized around a clear pipeline:

```
DOCX → JSON → Markdown → HTML → Website
                ↓
            Embeddings → Timeline
                ↓
                PDF
```

Each stage has its own script in `scripts/`:

| Script | Purpose |
|--------|---------|
| `parse_docx.py` | Extract entries from DOCX |
| `build.py` | Incremental DOCX → Markdown |
| `generate_html.py` | Markdown → HTML |
| `generate_embeddings.py` | Create embeddings for search |
| `generate_pdf.py` | Generate PDF output |

## License

Family project - use as you wish for your own family journals.
