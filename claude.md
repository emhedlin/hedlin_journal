# Hedlin Family Journal

## Overview

Static site generator converting DOCX journal files to a GitHub Pages website with an interactive timeline.

**Build Pipeline**: DOCX → JSON → Markdown → HTML → Website

## Project Structure

```
hedlin_journal/
├── docs/                  # Source DOCX journal files
├── content/               # Generated Markdown files (YYYY/MM structure)
├── data/                  # JSON entries, build state, embeddings
├── output/                # Final static website (deployed to GitHub Pages)
├── scripts/               # Python build scripts
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JavaScript, images
└── config.toml           # Site configuration (colors, title, etc.)
```

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_all.py` | Main orchestrator - runs full build pipeline |
| `scripts/parse_docx.py` | Extract entries and images from DOCX files |
| `scripts/build.py` | Incremental build with SHA256 change detection |
| `scripts/json_to_markdown.py` | Convert JSON to Markdown with YAML frontmatter |
| `scripts/generate_html.py` | Render HTML from Jinja2 templates |
| `scripts/generate_embeddings.py` | Create sentence-transformer embeddings |
| `scripts/generate_pdf.py` | Generate PDF book using WeasyPrint |
| `scripts/serve.py` | Development server (localhost:8000) |

## Build Commands

```bash
# Full build (includes PDF and embeddings - slow)
python scripts/build_all.py

# Development build (skips PDF and embeddings - fast)
python scripts/build_all.py --dev

# Parse new DOCX files only
python scripts/parse_docx.py

# Serve locally for preview
python scripts/serve.py
```

## DOCX Date Format

Entries are detected by date patterns in the Word documents:

- Full format: `Saturday, July 23, 1983`
- Abbreviated: `Sunday, July 24` (year inferred from previous entry)

Images embedded in DOCX are automatically extracted to `content/images/`.

## Website Features

1. **Navigation** - 3-level accordion (Years → Months → Entries)
2. **Interactive Timeline** - Canvas-based with zoom, hover tooltips, image indicators
3. **Semantic Search** - Powered by sentence-transformer embeddings
4. **PDF Export** - Print-ready 6" × 9" book format

## Configuration

Edit `config.toml` for:
- Theme colors (greyscale palette)
- Preview word count
- Site title and subtitle

## Deployment

- **GitHub Pages**: Push to main branch triggers `.github/workflows/deploy.yml`
- **Netlify**: Configured via `netlify.toml`
- **Manual**: Deploy `output/` directory to any static host

## Key Dependencies

- `python-docx` - DOCX parsing
- `jinja2` - HTML templating
- `sentence-transformers` - Semantic search embeddings
- `weasyprint` - PDF generation

## Important Notes

- Build is incremental - only modified DOCX files are reprocessed
- Build state tracked in `data/build_state.json`
- All links forced to black color for consistency (see recent commits)
- Design is minimal grayscale with serif typography (Garamond, Georgia)
