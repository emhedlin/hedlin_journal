#!/usr/bin/env python3
"""
Convert parsed journal entries (JSON) to Markdown files with YAML frontmatter.

This script:
1. Reads the journal_entries.json file created by the build script
2. Creates Markdown files organized by year/month
3. Preserves images in the content/images directory
4. Generates clean, git-friendly Markdown files
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Remove special chars, keep alphanumeric and spaces
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens
    text = re.sub(r'[-\s]+', '-', text)
    # Convert to lowercase and limit length
    return text.lower().strip('-')[:50]


def create_frontmatter(entry: Dict) -> str:
    """Create YAML frontmatter for an entry."""
    lines = ["---"]

    # Title (optional - generate from date if not present)
    if entry.get('title'):
        lines.append(f'title: "{entry["title"]}"')
    else:
        lines.append(f'title: "{entry.get("date_display", entry["date"])}"')

    # Date (required)
    lines.append(f'date: "{entry["date"]}"')

    # Original date display (required)
    lines.append(f'date_display: "{entry.get("date_display", "")}"')

    # Tags (optional - empty list if not present)
    tags = entry.get('tags', [])
    if tags:
        tags_str = json.dumps(tags)
        lines.append(f'tags: {tags_str}')
    else:
        lines.append('tags: []')

    # People mentioned (optional - empty list for now)
    # This could be enhanced with NLP later
    people = entry.get('people', [])
    if people:
        people_str = json.dumps(people)
        lines.append(f'people: {people_str}')
    else:
        lines.append('people: []')

    # Images (optional)
    images = entry.get('images', [])
    if images:
        images_str = json.dumps(images)
        lines.append(f'images: {images_str}')
    else:
        lines.append('images: []')

    # Source file (for tracking)
    lines.append(f'source_file: "{entry.get("source_file", "")}"')

    lines.append("---")
    return '\n'.join(lines)


def clean_content(content: str) -> str:
    """
    Clean and format content for Markdown.

    - Ensures proper paragraph spacing
    - Handles special characters
    - Preserves quotes and formatting
    """
    if not content:
        return ""

    # Split into paragraphs and rejoin with double newlines
    paragraphs = content.split('\n')
    # Remove empty paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    # Rejoin
    return '\n\n'.join(paragraphs)


def convert_to_markdown(
    data_file: Path,
    output_dir: Path,
    force: bool = False
) -> int:
    """
    Convert JSON entries to Markdown files.

    Returns 0 on success, 1 on error.
    """
    # Load JSON data
    if not data_file.exists():
        console.print(f"[red]Data file not found: {data_file}[/red]")
        return 1

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data.get('entries', [])

    if not entries:
        console.print("[yellow]No entries found in data file[/yellow]")
        return 0

    console.print(f"[bold]Converting {len(entries)} entries to Markdown[/bold]")

    # Create output directory structure
    content_dir = output_dir / "content"
    images_dir = output_dir / "content" / "images"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Track stats
    created = 0
    updated = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing entries...", total=len(entries))

        for entry in entries:
            progress.update(task, advance=1)

            date_str = entry.get('date', '')
            if not date_str:
                console.print(f"[yellow]Skipping entry without date[/yellow]")
                skipped += 1
                continue

            try:
                date_obj = datetime.fromisoformat(date_str)
            except ValueError:
                console.print(f"[yellow]Skipping entry with invalid date: {date_str}[/yellow]")
                skipped += 1
                continue

            # Create directory structure: content/YYYY/MM/
            year_dir = content_dir / str(date_obj.year)
            month_dir = year_dir / f"{date_obj.month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename: YYYY-MM-DD-slug.md
            slug = slugify(entry.get('date_display', date_str))
            filename = f"{date_str}-{slug}.md"
            output_file = month_dir / filename

            # Check if file exists and compare
            if output_file.exists() and not force:
                # Simple check: compare sizes
                existing_content = output_file.read_text(encoding='utf-8')
                new_content = create_frontmatter(entry) + '\n\n' + clean_content(entry.get('content', ''))
                if len(existing_content) == len(new_content):
                    skipped += 1
                    continue

            # Create Markdown content
            frontmatter = create_frontmatter(entry)
            content_body = clean_content(entry.get('content', ''))
            markdown_content = f"{frontmatter}\n\n{content_body}\n"

            # Write file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            if output_file.exists():
                updated += 1
            else:
                created += 1

    # Print summary
    console.print("\n[bold]Conversion Summary[/bold]\n")
    console.print(f"  [green]Created:[/green] {created} files")
    console.print(f"  [yellow]Updated:[/yellow] {updated} files")
    console.print(f"  [dim]Skipped:[/dim] {skipped} files")
    console.print(f"\n[green]Markdown files written to:[/green] {content_dir}")

    # Show directory structure
    console.print("\n[bold]Directory Structure:[/bold]")
    for year_dir in sorted(content_dir.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            year = year_dir.name
            month_count = len([d for d in year_dir.iterdir() if d.is_dir()])
            entry_count = len(list(year_dir.glob("**/*.md")))
            console.print(f"  {year}/ - {month_count} month(s), {entry_count} entries")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Convert journal JSON entries to Markdown files"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("data/journal_entries.json"),
        help="Input JSON file (default: data/journal_entries.json)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("."),  # Project root
        help="Output directory (default: project root, creates content/ subdir)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing files even if unchanged"
    )

    args = parser.parse_args()

    return convert_to_markdown(
        data_file=args.input,
        output_dir=args.output,
        force=args.force
    )


if __name__ == "__main__":
    exit(main())
