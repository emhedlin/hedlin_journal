#!/usr/bin/env python3
"""
Generate PDF files from journal entries.

This script uses WeasyPrint to generate:
1. A complete journal PDF with all entries
2. Optional per-entry PDFs
3. Print-ready book format
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from weasyprint import HTML, CSS

console = Console()


def parse_markdown_file(filepath: Path) -> Dict:
    """Parse a Markdown file with YAML frontmatter."""
    content = filepath.read_text(encoding='utf-8')

    frontmatter = {}
    body_start = 0

    if content.startswith('---'):
        end_marker = content.find('---', 4)
        if end_marker != -1:
            frontmatter_text = content[4:end_marker]
            body_start = end_marker + 3

            for line in frontmatter_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    if value.startswith('[') and value.endswith(']'):
                        value = json.loads(value)
                    frontmatter[key] = value

    body = content[body_start:].strip()
    return {'frontmatter': frontmatter, 'body': body}


def markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown to HTML."""
    import markdown
    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    return md.convert(markdown_text)


def load_entries(content_dir: Path, image_base_url: str = "") -> List[Dict]:
    """Load all journal entries from Markdown files."""
    entries = []

    for md_file in sorted(content_dir.rglob("*.md")):
        parsed = parse_markdown_file(md_file)
        fm = parsed['frontmatter']

        date_str = fm.get('date', '')
        if not date_str:
            continue

        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            continue

        # Get images with full paths
        images = fm.get('images', [])
        if image_base_url:
            images = [f"{image_base_url}{img}" for img in images]

        # Convert content to HTML
        content_html = markdown_to_html(parsed['body'])

        entries.append({
            'date': date_str,
            'date_display': fm.get('date_display', date_str),
            'title': fm.get('title', date_str),
            'content_html': content_html,
            'images': images,
            'year': date_obj.year,
            'month': date_obj.month,
            'day': date_obj.day
        })

    # Sort by date ascending for print
    entries.sort(key=lambda e: e['date'])

    return entries


def generate_complete_pdf(
    entries: List[Dict],
    template_path: Path,
    output_path: Path,
    content_dir: Path
) -> None:
    """Generate a complete PDF with all entries."""

    env = Environment(loader=FileSystemLoader(template_path.parent))
    template = env.get_template(template_path.name)

    # Prepare entries with year grouping
    current_year = None
    grouped_entries = []
    for entry in entries:
        if current_year is None or entry['year'] != current_year:
            entry['new_year'] = True
            current_year = entry['year']
        else:
            entry['new_year'] = False
        grouped_entries.append(entry)

    # Render HTML
    html_content = template.render(
        entries=grouped_entries,
        generated_date=datetime.now().strftime("%B %d, %Y")
    )

    console.print("[bold]Generating PDF...[/bold]")

    # Create images URL mapping for WeasyPrint
    base_url = str(content_dir.absolute()) + '/'

    # Generate PDF - CSS is already in the template
    HTML(string=html_content, base_url=base_url).write_pdf(output_path)

    console.print(f"[green]PDF saved to:[/green] {output_path}")


def generate_entry_pdfs(
    entries: List[Dict],
    template_path: Path,
    output_dir: Path,
    content_dir: Path
) -> None:
    """Generate individual PDFs for each entry."""

    # Create simple entry template
    entry_template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {
                size: letter;
                margin: 1in;
            }
            body {
                font-family: "Garamond", "Georgia", serif;
                font-size: 11pt;
                line-height: 1.6;
            }
            h1 {
                text-align: center;
                text-decoration: underline;
            }
            p {
                text-align: justify;
                text-indent: 1em;
            }
            p:first-of-type {
                text-indent: 0;
            }
        </style>
    </head>
    <body>
        <h1>{{ entry.date_display }}</h1>
        {{ entry.content_html | safe }}
    </body>
    </html>
    """

    from jinja2 import Template
    entry_template = Template(entry_template_str)
    base_url = str(content_dir.absolute()) + '/'

    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating entry PDFs...", total=len(entries))

        for entry in entries:
            html_content = entry_template.render(entry=entry)

            pdf_path = output_dir / f"{entry['date']}.pdf"

            HTML(string=html_content, base_url=base_url).write_pdf(pdf_path)

            progress.update(task, advance=1)

    console.print(f"[green]Entry PDFs saved to:[/green] {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate PDF files from journal entries"
    )
    parser.add_argument(
        "--content", "-c",
        type=Path,
        default=Path("content"),
        help="Directory containing Markdown files (default: content/)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output"),
        help="Output directory for PDFs (default: output/)"
    )
    parser.add_argument(
        "--templates", "-t",
        type=Path,
        default=Path("templates"),
        help="Template directory (default: templates/)"
    )
    parser.add_argument(
        "--individual", "-i",
        action="store_true",
        help="Also generate individual PDFs for each entry"
    )
    parser.add_argument(
        "--name", "-n",
        type=str,
        default="hedlin_family_journal.pdf",
        help="Name of the output PDF file"
    )

    args = parser.parse_args()

    # Load entries
    console.print("[bold]Loading journal entries...[/bold]")
    entries = load_entries(args.content)
    console.print(f"  [green]Found {len(entries)} entries[/green]")

    if not entries:
        console.print("[yellow]No entries found![/yellow]")
        return 1

    # Create output directory
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate complete PDF
    pdf_path = output_dir / args.name
    generate_complete_pdf(
        entries=entries,
        template_path=args.templates / "print_all.html",
        output_path=pdf_path,
        content_dir=args.content
    )

    # Generate individual PDFs if requested
    if args.individual:
        individual_dir = output_dir / "individual_pdfs"
        generate_entry_pdfs(
            entries=entries,
            template_path=args.templates / "print_all.html",
            output_dir=individual_dir,
            content_dir=args.content
        )

    # Print summary
    console.print("\n[bold]PDF Generation Summary[/bold]\n")
    console.print(f"  Complete journal: {pdf_path}")
    if args.individual:
        console.print(f"  Individual PDFs: {individual_dir}")

    # Get file size
    file_size = pdf_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    console.print(f"  File size: {size_mb:.1f} MB")

    return 0


if __name__ == "__main__":
    exit(main())
