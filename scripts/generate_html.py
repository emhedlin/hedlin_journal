#!/usr/bin/env python3
"""
Generate static HTML from Markdown journal entries.

This script:
1. Reads all Markdown files in content/
2. Converts Markdown to HTML
3. Generates index, archive, timeline, and individual entry pages
4. Copies static assets
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import markdown
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

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


def load_entries(content_dir: Path) -> List[Dict]:
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

        # Get preview (first paragraph, stripped of HTML)
        preview_match = re.search(r'<p>(.*?)</p>', content_html, re.DOTALL)
        preview = ""
        if preview_match:
            # Strip HTML tags for preview
            preview_text = re.sub(r'<[^>]+>', '', preview_match.group(1))
            preview = preview_text[:150] + "..." if len(preview_text) > 150 else preview_text

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


def group_entries_by_year_month(entries: List[Dict]) -> List[Dict]:
    """Group entries by year and month for archive page."""
    years = {}

    for entry in entries:
        year = entry['year']
        month = entry['month']

        if year not in years:
            years[year] = {'count': 0, 'months': {}}

        years[year]['count'] += 1

        if month not in years[year]['months']:
            years[year]['months'][month] = []

        years[year]['months'][month].append(entry)

    # Convert to sorted list
    result = []
    for year in sorted(years.keys(), reverse=True):
        months = []
        for month in sorted(years[year]['months'].keys()):
            months.append({
                'name': MONTH_NAMES[month - 1],
                'number': month,
                'entries': years[year]['months'][month]
            })

        result.append({
            'year': year,
            'count': years[year]['count'],
            'months': months
        })

    return result


def generate_site(
    content_dir: Path,
    output_dir: Path,
    template_dir: Path,
    static_dir: Path,
    url_path: str = ""
) -> int:
    """Generate the static site."""

    # Load entries
    console.print("[bold]Loading journal entries...[/bold]")
    entries = load_entries(content_dir)
    console.print(f"  [green]Found {len(entries)} entries[/green]")

    if not entries:
        console.print("[yellow]No entries found![/yellow]")
        return 1

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader(template_dir))
    base_template = env.get_template('base.html')
    entry_template = env.get_template('entry.html')
    index_template = env.get_template('index.html')
    archive_template = env.get_template('archive.html')
    timeline_template = env.get_template('timeline.html')

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "static").mkdir(parents=True, exist_ok=True)
    (output_dir / "entries").mkdir(parents=True, exist_ok=True)

    # Common context
    common_context = {
        'url_path': url_path,
        'year': datetime.now().year
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating pages...", total=3)

        # Generate index page
        progress.update(task, description="Generating index...")
        entries_by_year = group_entries_by_year_month(entries)

        # Get years for navigation
        years = sorted(set(e['year'] for e in entries))

        index_html = index_template.render(
            **common_context,
            recent_entries=entries[:10],
            total_entries=len(entries),
            recent_count=10,
            years=[(y, sum(1 for e in entries if e['year'] == y)) for y in years]
        )
        (output_dir / "index.html").write_text(index_html, encoding='utf-8')
        progress.update(task, advance=1)

        # Generate archive page
        progress.update(task, description="Generating archive...")
        archive_html = archive_template.render(
            **common_context,
            entries_by_year=entries_by_year,
            years=years
        )
        (output_dir / "archive.html").write_text(archive_html, encoding='utf-8')
        progress.update(task, advance=1)

        # Generate timeline page
        progress.update(task, description="Generating timeline...")
        timeline_html = timeline_template.render(
            **common_context,
            years=years,
            entries=entries
        )
        (output_dir / "timeline.html").write_text(timeline_html, encoding='utf-8')
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

    # Write entry data for timeline (JSON)
    entry_data = {
        'entries': [
            {
                'date': e['date'],
                'title': e['title'],
                'preview': e['preview'],
                'url': e['url'],
                'has_images': len(e.get('images', [])) > 0
            }
            for e in entries
        ]
    }
    (output_dir / "static" / "js" / "entries.json").write_text(
        json.dumps(entry_data, indent=2),
        encoding='utf-8'
    )

    console.print(f"\n[green]Site generated successfully![/green]")
    console.print(f"[green]Output directory:[/green] {output_dir}")
    console.print(f"  [dim]index.html, archive.html, timeline.html[/dim]")
    console.print(f"  [dim]{len(entries)} entry pages[/dim]")

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

    args = parser.parse_args()

    return generate_site(
        content_dir=args.content,
        output_dir=args.output,
        template_dir=args.templates,
        static_dir=args.static,
        url_path=args.url_path
    )


if __name__ == "__main__":
    exit(main())
