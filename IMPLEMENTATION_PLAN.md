# Hedlin Family Journal - Implementation Plan

## Project Overview
A static web-based family journal with an interactive timeline for navigating entries. Journal entries are stored in DOCX format and converted to a web-friendly format during build.

**Status: ALL STAGES COMPLETE ✓**

---

## Stage 1: Project Setup and DOCX Parsing ✓
**Status**: Complete

**Deliverables**:
- Project scaffold created with build system
- DOCX files parsed into structured JSON/Markdown
- Entry metadata (date, title, content, images) extracted correctly
- Incremental build support (only processes changed files)

**Technical Decisions**:
- **Language**: Python 3.11+ (for DOCX parsing and build pipeline)
- **Static Site Generator**: Custom HTML generation with Jinja2
- **DOCX Library**: `python-docx` for parsing

**Files Created**:
- `scripts/parse_docx.py` - DOCX parser with image extraction
- `scripts/build.py` - Incremental build script
- `data/build_state.json` - Tracks processed files

---

## Stage 2: Content Storage and Management ✓
**Status**: Complete

**Deliverables**:
- Parsed entries stored in Markdown format
- YAML frontmatter schema defined
- Content organized by year/month
- Git-friendly storage

**Technical Decisions**:
- **Storage Format**: Markdown files with YAML frontmatter
- **Directory Structure**: `content/YYYY/MM/entry-name.md`
- **Images**: `content/images/YYYY/MM/`

**Files Created**:
- `scripts/json_to_markdown.py` - JSON to Markdown converter
- `scripts/markdown_schema.md` - Frontmatter schema documentation
- Content structure in `content/` directory

---

## Stage 3: Build Pipeline and Static Site Generation ✓
**Status**: Complete

**Deliverables**:
- HTML pages generated for all entries
- Navigation between entries works
- Site can be built with a single command
- Classic journal aesthetic matching original DOCX

**Technical Decisions**:
- **Build Tool**: Custom Python script using Jinja2 templates
- **Styling**: Plain CSS with Garamond/serif fonts
- **Entry Pages**: Clean, readable, print-friendly

**Files Created**:
- `templates/base.html` - Base template
- `templates/entry.html` - Entry page
- `templates/index.html` - Home page
- `templates/archive.html` - Archive page
- `templates/timeline.html` - Timeline page
- `static/css/styles.css` - Complete styling with print support
- `scripts/generate_html.py` - HTML generator

---

## Stage 4: Interactive Timeline with Embeddings ✓
**Status**: Complete

**Deliverables**:
- Timeline renders with year/month ticks
- Hovering shows entry summaries
- Timeline is interactive (clickable, zoomable)
- Year filter implemented

**Technical Decisions**:
- **Timeline**: Custom Canvas implementation
- **Embeddings**: Pre-computed using sentence-transformers (all-MiniLM-L6-v2)
- **Search/Summarization**: Client-side filtering

**Files Created**:
- `scripts/generate_embeddings.py` - Embedding generator
- `static/js/timeline.js` - Interactive timeline component
- `output/static/js/embeddings.json` - Embeddings data (384 dimensions)

---

## Stage 5: PDF and Print Book Generation ✓
**Status**: Complete

**Deliverables**:
- PDF generation preserves formatting
- Book layout includes title page and TOC
- Output matches example.docx aesthetic
- Individual entry PDFs supported

**Technical Decisions**:
- **PDF Generation**: WeasyPrint
- **Book Format**: 6" × 9" with proper margins

**Files Created**:
- `templates/print_all.html` - Print template
- `scripts/generate_pdf.py` - PDF generator
- `output/hedlin_journal.pdf` - Complete journal PDF

---

## Stage 6: Polish and Deployment ✓
**Status**: Complete

**Deliverables**:
- Documentation complete (README.md)
- Deployment configurations added
- Unified build script
- Development server

**Files Created**:
- `README.md` - Complete documentation
- `scripts/build_all.py` - Unified build pipeline
- `scripts/serve.py` - Development server
- `scripts/journal.py` - Convenience commands
- `.github/workflows/deploy.yml` - GitHub Actions
- `netlify.toml` - Netlify configuration

---

## Technology Stack Summary

| Component | Technology |
|-----------|------------|
| Build Language | Python 3.11+ |
| Dependency Manager | uv |
| DOCX Parsing | python-docx |
| Templates | Jinja2 |
| Markdown | markdown |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Timeline | Custom Canvas API |
| Styling | Plain CSS |
| PDF Export | WeasyPrint |
| Deployment | GitHub Pages / Netlify |
| Version Control | Git |

---

## Quick Start

```bash
# Install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Build the site
python scripts/build_all.py --dev

# Start dev server
python scripts/serve.py
```

---

## File Structure

```
hedlin_journal/
├── content/              # Generated Markdown (gitignored)
│   ├── 1983/07/         # Entries by year/month
│   └── images/
├── data/                 # Build data (gitignored)
│   ├── build_state.json
│   └── journal_entries.json
├── docs/                 # Source DOCX files
│   └── *.docx
├── output/               # Generated website (gitignored)
│   ├── index.html
│   ├── timeline.html
│   ├── archive.html
│   ├── entries/
│   └── static/
├── scripts/              # Build and utility scripts
│   ├── build_all.py      # Main pipeline
│   ├── build.py          # DOCX → JSON → Markdown
│   ├── parse_docx.py     # DOCX parser
│   ├── generate_html.py  # Markdown → HTML
│   ├── generate_embeddings.py  # Embeddings
│   ├── generate_pdf.py   # PDF generation
│   ├── serve.py          # Dev server
│   └── journal.py        # Convenience commands
├── templates/            # Jinja2 templates
│   ├── base.html
│   ├── entry.html
│   ├── index.html
│   ├── archive.html
│   ├── timeline.html
│   └── print_all.html
├── static/               # CSS, JS
│   ├── css/styles.css
│   └── js/timeline.js
├── .github/workflows/    # CI/CD
│   └── deploy.yml
├── README.md             # Documentation
├── IMPLEMENTATION_PLAN.md
└── requirements.txt
```

---

## Build Pipeline

```
DOCX files → JSON → Markdown → HTML → Website
                      ↓
                  Embeddings → Timeline
                      ↓
                      PDF
```

All stages implemented and tested with 101 sample entries.
