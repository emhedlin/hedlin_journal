#!/usr/bin/env python3
"""
Complete build pipeline for the Hedlin Family Journal.

This script runs the full build process:
1. Parse source files (DOCX or Google Docs) to JSON
2. Convert to Markdown
3. Generate HTML website
4. Generate embeddings for timeline
5. Generate PDFs

Usage:
    python scripts/build_all.py [--source docx|gdocs] [--force] [--year YEAR]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Default configuration
DEFAULT_SOURCE = "docx"  # Can be overridden by config.toml


def run_step(name: str, cmd: list, cwd: Path = None) -> bool:
    """Run a build step and return success status."""
    console.print(f"\n[bold cyan]Step: {name}[/bold cyan]")
    console.print(f"[dim]{' '.join(cmd)}[/dim]")

    result = subprocess.run(
        cmd,
        cwd=cwd or Path.cwd(),
        capture_output=False
    )

    if result.returncode != 0:
        console.print(f"[red]✗ {name} failed[/red]")
        return False

    console.print(f"[green]✓ {name} complete[/green]")
    return True


def load_config() -> dict:
    """Load configuration from config.toml if it exists."""
    config_file = Path.cwd() / "config.toml"
    if config_file.exists():
        try:
            import tomli
            with open(config_file, 'rb') as f:
                return tomli.load(f)
        except ImportError:
            console.print("[yellow]tomli not installed, using default config[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Error loading config: {e}[/yellow]")
    return {}


def get_source(config: dict, arg_source: str = None) -> str:
    """Determine the source type from config or argument."""
    if arg_source:
        return arg_source
    # Check config.toml for source setting
    if 'source' in config:
        return config['source'].get('mode', DEFAULT_SOURCE)
    return DEFAULT_SOURCE


def get_gdocs_config(config: dict) -> dict:
    """Get Google Docs configuration."""
    return config.get('gdocs', {})


def run_fetch_from_gdocs(gdocs_config: dict, output_dir: Path) -> bool:
    """Run fetch_from_gdocs.py with appropriate configuration."""
    credentials = gdocs_config.get('credentials', 'credentials.json')
    folder_id = gdocs_config.get('folder_id', '')

    if not folder_id:
        console.print("[red]Error: gdocs.folder_id not configured in config.toml[/red]")
        return False

    if not Path(credentials).exists():
        console.print(f"[red]Error: Credentials file not found: {credentials}[/red]")
        console.print("\n[yellow]To set up Google Cloud:[/yellow]")
        console.print("1. Create a Google Cloud Project")
        console.print("2. Enable Docs API and Drive API")
        console.print("3. Create a service account and download credentials")
        console.print("4. Share your Drive folder with the service account")
        return False

    return run_step(
        "Fetch from Google Docs",
        ["python", "scripts/fetch_from_gdocs.py",
         "--credentials", credentials,
         "--folder-id", folder_id,
         "--output", str(output_dir)]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Complete build pipeline for Hedlin Family Journal"
    )
    parser.add_argument(
        "--source", "-s",
        type=str,
        choices=["docx", "gdocs"],
        default=None,
        help="Source type: 'docx' or 'gdocs' (default: from config.toml or 'docx')"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force rebuild of all files"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        default=None,
        help="Default year for abbreviated dates"
    )
    parser.add_argument(
        "--skip-pdf", "-p",
        action="store_true",
        help="Skip PDF generation (faster builds)"
    )
    parser.add_argument(
        "--skip-embeddings", "-e",
        action="store_true",
        help="Skip embedding generation (faster builds)"
    )
    parser.add_argument(
        "--dev", "-d",
        action="store_true",
        help="Development mode: skip PDFs and embeddings"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Determine source type
    source = get_source(config, args.source)
    gdocs_config = get_gdocs_config(config)

    # Dev mode shortcuts
    if args.dev:
        args.skip_pdf = True
        args.skip_embeddings = True

    # Start time
    start_time = datetime.now()

    console.print(Panel.fit(
        "[bold cyan]Hedlin Family Journal[/bold cyan]\n"
        f"Complete Build Pipeline [dim](source: {source})[/dim]",
        border_style="cyan"
    ))

    data_dir = Path("data")
    steps = []

    # Step 1: Fetch/Parse entries based on source
    if source == "gdocs":
        # Fetch from Google Docs (produces journal_entries.json)
        if not run_fetch_from_gdocs(gdocs_config, data_dir):
            console.print("[red]Failed to fetch from Google Docs[/red]")
            return 1
        # Convert JSON to Markdown
        steps.append((
            "Convert JSON to Markdown",
            ["python", "scripts/json_to_markdown.py",
             "-i", str(data_dir / "journal_entries.json"),
             "-o", "content"]
        ))
    else:
        # Parse DOCX files
        base_args = ["-i", "docs", "-d", str(data_dir), "-o", "."]
        if args.force:
            base_args.append("--force")
        if args.year:
            base_args.extend(["--year", str(args.year)])

        steps.append((
            "Parse DOCX & Generate Markdown",
            ["python", "scripts/build.py"] + base_args
        ))

    # Step 2: Generate HTML website
    steps.append((
        "Generate HTML Website",
        ["python", "scripts/generate_html.py", "-c", "content", "-o", "output", "-t", "templates", "-s", "static"]
    ))

    # Step 3: Generate embeddings (skip if requested)
    if not args.skip_embeddings:
        steps.append((
            "Generate Embeddings",
            ["python", "scripts/generate_embeddings.py", "-i", "data/journal_entries.json", "-o", "output/static/js/embeddings.json"]
        ))

    # Step 4: Generate PDFs (skip if requested)
    if not args.skip_pdf:
        steps.append((
            "Generate PDFs",
            ["python", "scripts/generate_pdf.py", "-c", "content", "-o", "output", "-t", "templates", "-n", "hedlin_journal.pdf"]
        ))

    # Run all steps
    failed = []
    for step_name, step_cmd in steps:
        if not run_step(step_name, step_cmd):
            failed.append(step_name)

    # Summary
    duration = (datetime.now() - start_time).total_seconds()

    console.print("\n" + "=" * 50)
    console.print("[bold]Build Summary[/bold]\n")

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Duration", f"{duration:.1f} seconds")
    table.add_row("Status", "[green]Success[/green]" if not failed else "[red]Failed[/red]")

    if args.skip_pdf:
        table.add_row("PDFs", "[dim]Skipped[/dim]")
    if args.skip_embeddings:
        table.add_row("Embeddings", "[dim]Skipped[/dim]")

    console.print(table)

    # Output locations
    console.print("\n[bold]Output Locations:[/bold]")
    console.print("  [cyan]Website:[/cyan]   output/index.html")
    console.print("  [cyan]Timeline:[/cyan]  output/timeline.html")
    console.print("  [cyan]Archive:[/cyan]   output/archive.html")
    if not args.skip_pdf:
        console.print("  [cyan]PDF:[/cyan]       output/hedlin_journal.pdf")

    # Preview command
    console.print("\n[bold]To preview locally:[/bold]")
    console.print("  [dim]python -m http.server 8000 --directory output[/dim]")

    if failed:
        console.print(f"\n[red]Failed steps: {', '.join(failed)}[/red]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
