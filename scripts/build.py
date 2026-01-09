#!/usr/bin/env python3
"""
Build script for the Hedlin Family Journal.

This script handles incremental updates from DOCX files:
1. Tracks which files have been processed
2. Detects new or modified DOCX files
3. Only reprocesses changed files
4. Merges new entries with existing data
"""

import argparse
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from parse_docx import find_docx_files, parse_docx_file, JournalEntry

console = Console()


@dataclass
class BuildState:
    """Tracks the state of processed files."""
    files: Dict[str, str]  # filename -> SHA256 hash
    last_build: str
    total_entries: int


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_build_state(state_file: Path) -> BuildState:
    """Load the previous build state."""
    if state_file.exists():
        data = json.loads(state_file.read_text())
        return BuildState(
            files=data.get('files', {}),
            last_build=data.get('last_build', ''),
            total_entries=data.get('total_entries', 0)
        )
    return BuildState(files={}, last_build='', total_entries=0)


def save_build_state(state_file: Path, state: BuildState):
    """Save the current build state."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(asdict(state), f, indent=2)


def load_existing_entries(data_file: Path) -> List[dict]:
    """Load previously parsed entries."""
    if data_file.exists():
        data = json.loads(data_file.read_text())
        return data.get('entries', [])
    return []


def merge_entries(
    existing: List[dict],
    new_entries: List[JournalEntry],
    source_files: List[str]
) -> List[dict]:
    """
    Merge new entries with existing ones.

    Strategy:
    1. Remove all entries from the source files that were re-processed
    2. Add the new entries from those files
    3. Keep entries from other files unchanged
    """
    # Create a set of entries to remove (from reprocessed files)
    entries_to_remove = {entry['date'] for entry in existing if entry['source_file'] in source_files}

    # Keep entries not from reprocessed files
    merged = [e for e in existing if e['source_file'] not in source_files]

    # Add new entries
    for entry in new_entries:
        entry_dict = {
            'date': entry.date,
            'date_display': entry.date_display,
            'title': entry.title,
            'content': entry.content,
            'images': entry.images or [],
            'source_file': entry.source_file
        }
        merged.append(entry_dict)

    # Sort by date
    merged.sort(key=lambda e: e['date'])

    return merged


def convert_to_markdown(entries_file: Path, output_dir: Path, force: bool = False) -> int:
    """Convert JSON entries to Markdown files."""
    import re
    from json_to_markdown import slugify, clean_content

    # Load JSON data
    with open(entries_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data.get('entries', [])
    if not entries:
        return 0

    # Create output directory structure
    content_dir = output_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    created = 0

    for entry in entries:
        date_str = entry.get('date', '')
        if not date_str:
            continue

        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            continue

        # Create directory: content/YYYY/MM/
        year_dir = content_dir / str(date_obj.year)
        month_dir = year_dir / f"{date_obj.month:02d}"
        month_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        slug = slugify(entry.get('date_display', date_str))
        filename = f"{date_str}-{slug}.md"
        output_file = month_dir / filename

        # Create frontmatter
        tags = entry.get('tags', [])
        people = entry.get('people', [])
        images = entry.get('images', [])

        frontmatter = f"""---
title: "{entry.get('date_display', date_str)}"
date: "{date_str}"
date_display: "{entry.get('date_display', '')}"
tags: {json.dumps(tags)}
people: {json.dumps(people)}
images: {json.dumps(images)}
source_file: "{entry.get('source_file', '')}"
---

"""

        content_body = clean_content(entry.get('content', ''))
        markdown_content = frontmatter + content_body + "\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        created += 1

    console.print(f"  [green]Created {created} Markdown files in:[/green] {content_dir}")
    return 0


def build(
    docs_dir: Path,
    data_dir: Path,
    output_dir: Path,
    force: bool = False,
    default_year: Optional[int] = None,
    markdown: bool = True
) -> int:
    """
    Run the incremental build process.

    Returns 0 on success, 1 on error.
    """
    state_file = data_dir / "build_state.json"
    entries_file = data_dir / "journal_entries.json"

    # Load previous state
    state = load_build_state(state_file)

    # Find all DOCX files
    docx_files = find_docx_files(docs_dir)

    if not docx_files:
        console.print("[red]No DOCX files found[/red]")
        return 1

    # Check for changes
    changed_files = []
    unchanged_files = []
    current_hashes = {}

    for docx_file in docx_files:
        file_hash = compute_file_hash(docx_file)
        current_hashes[docx_file.name] = file_hash

        if force or docx_file.name not in state.files or state.files[docx_file.name] != file_hash:
            changed_files.append(docx_file)
        else:
            unchanged_files.append(docx_file)

    # Report status
    if changed_files:
        console.print(f"\n[bold yellow]Files to process:[/bold yellow] {len(changed_files)}")
        for f in changed_files:
            console.print(f"  - {f.name}")
    else:
        console.print("[green]No changes detected. All files up to date.[/green]")
        return 0

    if unchanged_files:
        console.print(f"\n[dim]Unchanged files:[/dim] {len(unchanged_files)}")

    # Load existing entries
    existing_entries = load_existing_entries(entries_file)

    # Parse changed files
    all_new_entries: List[JournalEntry] = []
    processed_files = []

    for docx_file in changed_files:
        parsed = parse_docx_file(docx_file, Path.cwd(), default_year)
        all_new_entries.extend(parsed.entries)
        processed_files.append(docx_file.name)

    # Merge entries
    merged_entries = merge_entries(existing_entries, all_new_entries, processed_files)

    # Create output data
    output_data = {
        "title": "Hedlin Family Journal",
        "parsed_at": datetime.now().isoformat(),
        "last_updated_files": processed_files,
        "entries": merged_entries
    }

    # Write output
    entries_file.parent.mkdir(parents=True, exist_ok=True)
    with open(entries_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Update state
    new_state = BuildState(
        files={**state.files, **current_hashes},
        last_build=datetime.now().isoformat(),
        total_entries=len(merged_entries)
    )
    save_build_state(state_file, new_state)

    # Convert to Markdown
    if markdown:
        console.print("\n[bold]Converting to Markdown...[/bold]")
        convert_to_markdown(entries_file, output_dir, force)

    # Print summary table
    console.print("\n[bold]Build Summary[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Files processed", str(len(changed_files)))
    table.add_row("Files unchanged", str(len(unchanged_files)))
    table.add_row("New entries added", str(len(all_new_entries)))
    table.add_row("Total entries", str(len(merged_entries)))

    console.print(table)

    console.print(f"\n[green]Data written to:[/green] {entries_file}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Incrementally build the Hedlin Family Journal"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("docs"),
        help="Directory containing DOCX files (default: docs/)"
    )
    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        default=Path("data"),
        help="Directory for build data (default: data/)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output"),
        help="Directory for final output (default: output/)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force reprocessing of all files"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        default=None,
        help="Default year for abbreviated dates"
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip Markdown conversion"
    )

    args = parser.parse_args()

    return build(
        docs_dir=args.input,
        data_dir=args.data_dir,
        output_dir=args.output,
        force=args.force,
        default_year=args.year,
        markdown=not args.no_markdown
    )


if __name__ == "__main__":
    exit(main())
