#!/usr/bin/env python3
"""
Complete build pipeline for the Hedlin Family Journal.

This script runs the full build process:
1. Parse DOCX files to JSON
2. Convert to Markdown
3. Generate HTML website
4. Generate embeddings for timeline
5. Generate PDFs

Usage:
    python scripts/build_all.py [--force] [--year YEAR]
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


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


def main():
    parser = argparse.ArgumentParser(
        description="Complete build pipeline for Hedlin Family Journal"
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

    # Dev mode shortcuts
    if args.dev:
        args.skip_pdf = True
        args.skip_embeddings = True

    # Start time
    start_time = datetime.now()

    console.print(Panel.fit(
        "[bold cyan]Hedlin Family Journal[/bold cyan]\n"
        "Complete Build Pipeline",
        border_style="cyan"
    ))

    # Base command arguments
    base_args = ["-i", "docs", "-d", "data", "-o", "."]
    if args.force:
        base_args.append("--force")
    if args.year:
        base_args.extend(["--year", str(args.year)])

    steps = []

    # Step 1: Build (DOCX → JSON → Markdown)
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
