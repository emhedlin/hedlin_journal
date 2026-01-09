#!/usr/bin/env python3
"""
Development server for the Hedlin Family Journal.

This script starts a simple HTTP server to preview the generated site.
"""

import argparse
import http.server
import socketserver
import webbrowser
from pathlib import Path

from rich.console import Console

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Start development server for Hedlin Family Journal"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to run server on (default: 8000)"
    )
    parser.add_argument(
        "--directory", "-d",
        type=Path,
        default=Path("output"),
        help="Directory to serve (default: output/)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )

    args = parser.parse_args()

    if not args.directory.exists():
        console.print(f"[red]Error: Directory {args.directory} does not exist![/red]")
        console.print(f"[yellow]Run 'python scripts/build_all.py' first.[/yellow]")
        return 1

    # Change to the output directory
    import os
    os.chdir(args.directory)

    # Create custom handler
    class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress log messages

    # Start server
    with socketserver.TCPServer(("", args.port), QuietHTTPRequestHandler) as httpd:
        url = f"http://localhost:{args.port}"
        console.print(Panel.fit(
            f"[bold green]Development Server Running[/bold green]\n\n"
            f"URL: [cyan]{url}[/cyan]\n"
            f"Directory: [dim]{args.directory.absolute()}[/dim]\n\n"
            f"Press Ctrl+C to stop",
            border_style="green"
        ))

        if not args.no_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped[/yellow]")

    return 0


if __name__ == "__main__":
    exit(main())
