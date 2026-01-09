#!/usr/bin/env python3
"""
Generate static HTML from Markdown journal entries.

This script:
1. Reads all Markdown files in content/
2. Converts Markdown to HTML
3. Generates index, archive, and individual entry pages
4. Copies static assets
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import markdown
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from load_config import load_config

console = Console()

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def parse_markdown_file(filepath: Path) -> Dict:
    """Parse a Markdown file with YAML frontmatter."""
    content = filepath.read_text(encoding='utf-8')

    # Extract frontmatter
    frontmatter = {}
    body_start = 0

    if content.startswith('---'):
        end_marker = content.find('---', 4)
        if end_marker != -1:
            frontmatter_text = content[4:end_marker]
            body_start = end_marker + 3

            # Parse YAML-like frontmatter
            for line in frontmatter_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    # Handle lists
                    if value.startswith('[') and value.endswith(']'):
                        value = json.loads(value)
                    frontmatter[key] = value

    # Get body content
    body = content[body_start:].strip()

    return {
        'frontmatter': frontmatter,
        'body': body
    }


def markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown to HTML."""
    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    return md.convert(markdown_text)


def get_entry_preview(content: str, word_count: int = 8) -> str:
    """Get first N words from content as preview."""
    # Strip HTML tags for preview
    text = re.sub(r'<[^>]+>', '', content)
    words = text.split()[:word_count]
    return ' '.join(words)


def load_entries(content_dir: Path, config) -> List[Dict]:
    """Load all journal entries from Markdown files."""
    entries = []

    for md_file in content_dir.rglob("*.md"):
        parsed = parse_markdown_file(md_file)
        fm = parsed['frontmatter']

        date_str = fm.get('date', '')
        if not date_str:
            continue

        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            continue

        # Generate URL path
        url_path = f"/entries/{date_obj.year}/{date_obj.month:02d}/{md_file.stem}.html"

        # Convert content to HTML
        content_html = markdown_to_html(parsed['body'])

        # Get preview
        preview = get_entry_preview(content_html, config.preview.word_count)

        entries.append({
            'date': date_str,
            'date_display': fm.get('date_display', date_str),
            'title': fm.get('title', date_str),
            'content_html': content_html,
            'preview': preview,
            'url': url_path,
            'tags': fm.get('tags', []),
            'people': fm.get('people', []),
            'images': fm.get('images', []),
            'source_file': fm.get('source_file', ''),
            'year': date_obj.year,
            'month': date_obj.month,
            'day': date_obj.day
        })

    # Sort by date descending
    entries.sort(key=lambda e: e['date'], reverse=True)

    return entries


def build_year_hierarchy(entries: List[Dict]) -> tuple:
    """Build data structures for accordion navigation.

    Returns:
        - years: List of year dicts with year and has_entries
        - months_by_year: Data structure with months for each year
    """
    if not entries:
        return [], []

    # Find min year from entries (or default to 1983)
    min_year_from_entries = min(e['year'] for e in entries)
    start_year = min(1983, min_year_from_entries)

    # Current year
    current_year = datetime.now().year

    # Group entries by year-month
    year_month_entries = {}
    for entry in entries:
        year = entry['year']
        month = entry['month']
        key = (year, month)

        if key not in year_month_entries:
            year_month_entries[key] = []
        year_month_entries[key].append(entry)

    # Build years list (full range 1983 -> current year)
    years = []
    for year in range(start_year, current_year + 1):
        year_entries = [e for e in entries if e['year'] == year]
        years.append({
            'year': year,
            'has_entries': len(year_entries) > 0
        })

    # Build months_by_year structure
    months_by_year = []
    for year in range(start_year, current_year + 1):
        year_data = {
            'year': year,
            'months': []
        }

        for month in range(1, 13):
            # Check if there are entries for this year-month
            month_entries = year_month_entries.get((year, month), [])
            # Sort entries by day ascending (oldest first)
            month_entries = sorted(month_entries, key=lambda e: e['day'])
            has_entries = len(month_entries) > 0

            month_name = MONTH_NAMES[month - 1]

            year_data['months'].append({
                'name': month_name,
                'number': month,
                'has_entries': has_entries,
                'entries': month_entries
            })

        months_by_year.append(year_data)

    return years, months_by_year


def generate_site(
    content_dir: Path,
    output_dir: Path,
    template_dir: Path,
    static_dir: Path,
    url_path: str = "",
    config_file: Path = None
) -> int:
    """Generate the static site."""

    # Load configuration
    config = load_config(config_file)
    config_css = config.to_css_vars()

    # Load entries
    console.print("[bold]Loading journal entries...[/bold]")
    entries = load_entries(content_dir, config)
    console.print(f"  [green]Found {len(entries)} entries[/green]")

    if not entries:
        console.print("[yellow]No entries found![/yellow]")
        return 1

    # Build navigation data
    years, months_by_year = build_year_hierarchy(entries)

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader(template_dir))
    base_template = env.get_template('base.html')
    entry_template = env.get_template('entry.html')
    index_template = env.get_template('index.html')

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "static").mkdir(parents=True, exist_ok=True)
    (output_dir / "entries").mkdir(parents=True, exist_ok=True)

    # Common context
    common_context = {
        'config': config,
        'config_css': config_css,
        'url_path': url_path,
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating pages...", total=2)

        # Generate index page with accordion navigation
        progress.update(task, description="Generating index...")
        index_html = index_template.render(
            **common_context,
            years=years,
            months_by_year=months_by_year
        )
        (output_dir / "index.html").write_text(index_html, encoding='utf-8')
        progress.update(task, advance=1)

        # Generate entry pages
        task2 = progress.add_task("Generating entry pages...", total=len(entries))

        for i, entry in enumerate(entries):
            # Find prev/next entries
            prev_entry = entries[i + 1] if i < len(entries) - 1 else None
            next_entry = entries[i - 1] if i > 0 else None

            entry_html = entry_template.render(
                **common_context,
                entry={
                    **entry,
                    'prev': prev_entry['url'] if prev_entry else None,
                    'next': next_entry['url'] if next_entry else None
                }
            )

            # Create directory structure
            entry_path = output_dir / entry['url'].lstrip('/')
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            entry_path.write_text(entry_html, encoding='utf-8')

            progress.update(task2, advance=1)

    # Copy static files
    console.print("[bold]Copying static files...[/bold]")

    # Copy CSS
    css_output = output_dir / "static" / "css"
    css_output.mkdir(parents=True, exist_ok=True)
    for css_file in static_dir.glob("css/*.css"):
        import shutil
        shutil.copy(css_file, css_output / css_file.name)
        console.print(f"  [dim]{css_file.name}[/dim]")

    # Copy JS
    js_output = output_dir / "static" / "js"
    js_output.mkdir(parents=True, exist_ok=True)
    for js_file in static_dir.glob("js/*.js"):
        if js_file.is_file():
            import shutil
            shutil.copy(js_file, js_output / js_file.name)
            console.print(f"  [dim]{js_file.name}[/dim]")

    # Copy images
    if (content_dir / "images").exists():
        images_output = output_dir / "content" / "images"
        import shutil
        shutil.copytree(content_dir / "images", images_output, dirs_exist_ok=True)
        console.print(f"  [dim]images/[/dim]")

    console.print(f"\n[green]Site generated successfully![/green]")
    console.print(f"[green]Output directory:[/green] {output_dir}")
    console.print(f"  [dim]index.html, {len(entries)} entry pages[/dim]")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate static HTML from Markdown journal entries"
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
        help="Output directory for generated site (default: output/)"
    )
    parser.add_argument(
        "--templates", "-t",
        type=Path,
        default=Path("templates"),
        help="Template directory (default: templates/)"
    )
    parser.add_argument(
        "--static", "-s",
        type=Path,
        default=Path("static"),
        help="Static files directory (default: static/)"
    )
    parser.add_argument(
        "--url-path", "-u",
        type=str,
        default="",
        help="URL path prefix (e.g., '/journal')"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Configuration file (default: config.toml)"
    )

    args = parser.parse_args()

    return generate_site(
        content_dir=args.content,
        output_dir=args.output,
        template_dir=args.templates,
        static_dir=args.static,
        url_path=args.url_path,
        config_file=args.config
    )


if __name__ == "__main__":
    exit(main())
